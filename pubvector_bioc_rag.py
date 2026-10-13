#!/usr/bin/env python3
"""
PubVector — PubMed/PMC Knowledge Base Builder (single-file app)
===============================================================

A self-contained tool that searches PubMed/PMC for review articles and case
reports matching user-supplied keywords, fetches structured full text, extracts
narratives, downloads PDFs/images, and prepares RAG-ready chunks.

This single file works two ways:

  1. As a Streamlit web app (default when launched with Streamlit):
         streamlit run pubvector.py

  2. As a command-line pipeline:
         python pubvector.py --email you@uni.edu --keywords "Fabry disease" ...
         python pubvector.py --list-diseases

Install
-------
    python -m pip install -r requirements.txt
    # (streamlit pandas pyarrow biopython requests beautifulsoup4 lxml tqdm)

Notes
-----
- Outputs are written to the chosen output directory (parquet, jsonl,
  publication_summary.txt, run_summary.json), identical in both modes.
- The pipeline runs in a background thread in the web app, with live logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import queue
import re
import sys
import tarfile
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urljoin

import pandas as pd
import requests
from Bio import Entrez
from bs4 import BeautifulSoup
from tqdm import tqdm

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("raredx")


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

NCBI_RATE_LIMIT_NO_KEY = 0.35
NCBI_RATE_LIMIT_WITH_KEY = 0.12
EUROPEPMC_RATE_LIMIT = 0.2

BIOC_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"
PMC_OA_SERVICE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
PMC_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/"

DEFAULT_USER_AGENT = "RareDx-Pipeline/1.0"


# ---------------------------------------------------------------------
# Article-type classes
# ---------------------------------------------------------------------
#
# Each class is an internal key (used on the CLI, in provenance, and as the
# `article_type` tag on every record) mapped to:
#
#   label     : human-readable name shown in the Streamlit UI.
#   pt        : exact PubMed Publication Type [pt] tokens. These MUST match
#               NLM's spelling verbatim (e.g. "Case Reports" is plural,
#               "Meta-Analysis" is hyphenated). A typo silently matches
#               nothing, the same failure mode as '"open access"[filter]'.
#   tiab      : free-text [tiab] fallbacks OR-ed in alongside the [pt] tokens
#               to recover recent / not-yet-indexed articles that lack a PT.
#   pt_match  : lowercase substrings used to classify an article *after* the
#               fact, from its PubMed PublicationTypeList, into this class.
#               Order in ARTICLE_TYPE_CLASSES is the classification priority.
#   narrative : if True, records of this class are segmented for a case
#               narrative (CASE_SECTION_RE); otherwise full body text is kept.
#
# Publication Type strings are drawn from NLM's authoritative list
# (https://www.ncbi.nlm.nih.gov/books/NBK3799/). PT searches are NOT exploded,
# so sibling types (Review vs Systematic Review vs Meta-Analysis) must each be
# listed explicitly within a class.

ARTICLE_TYPE_CLASSES: dict[str, dict[str, Any]] = {
    "review": {
        "label": "Evidence synthesis (reviews)",
        "pt": ["Review", "Systematic Review", "Meta-Analysis"],
        "tiab": [
            "review", "systematic review", "meta-analysis", "meta analysis",
        ],
        "pt_match": ["review", "meta-analysis", "meta analysis"],
        "narrative": False,
    },
    "trial": {
        "label": "Clinical trials & studies",
        "pt": [
            "Randomized Controlled Trial", "Clinical Trial",
            "Controlled Clinical Trial", "Observational Study",
            "Multicenter Study", "Clinical Trial Protocol",
        ],
        "tiab": [
            "randomized controlled trial", "randomised controlled trial",
            "clinical trial", "observational study",
        ],
        "pt_match": [
            "randomized controlled trial", "clinical trial",
            "controlled clinical trial", "observational study",
            "multicenter study",
        ],
        "narrative": False,
    },
    "case_report": {
        "label": "Case reports & series",
        "pt": ["Case Reports"],
        "tiab": [
            "case report", "case reports", "case series", "clinical case",
        ],
        "pt_match": ["case report"],
        "narrative": True,
    },
    "guideline": {
        "label": "Guidance & consensus",
        "pt": [
            "Practice Guideline", "Guideline",
            "Consensus Development Conference",
        ],
        "tiab": [
            "practice guideline", "clinical guideline", "consensus statement",
        ],
        "pt_match": [
            "practice guideline", "guideline",
            "consensus development conference",
        ],
        "narrative": False,
    },
    "commentary": {
        "label": "Commentary & news",
        "pt": ["Editorial", "Letter", "Comment", "News", "Preprint"],
        "tiab": ["editorial", "commentary"],
        "pt_match": ["editorial", "letter", "comment", "news", "preprint"],
        "narrative": False,
    },
}

# Default selection preserves the original tool's behaviour.
DEFAULT_ARTICLE_TYPES = ["review", "case_report"]

# Reverse map: Streamlit display label -> internal key.
ARTICLE_TYPE_LABEL_TO_KEY = {
    spec["label"]: key for key, spec in ARTICLE_TYPE_CLASSES.items()
}


def classify_publication_types(pub_types: set[str]) -> list[str]:
    """Map a set of lowercased PubMed PublicationType strings to class keys.

    Returns class keys in registry order (which encodes priority), so an
    article tagged both "Review" and "Case Reports" is labelled
    "review;case_report" deterministically.
    """
    matched: list[str] = []
    for key, spec in ARTICLE_TYPE_CLASSES.items():
        if any(
            needle in pt
            for needle in spec["pt_match"]
            for pt in pub_types
        ):
            matched.append(key)
    return matched


# ---------------------------------------------------------------------
# Disease panel and synonym expansion
# ---------------------------------------------------------------------
#
# Keys are the canonical disease labels (as supplied by the user); these are
# stored verbatim as the "disease" tag on every record. Values are lists of
# PubMed search terms (synonyms / expansions). At query time each term is
# searched in [Title/Abstract] and the list is OR-ed together, so that
# abbreviations like "ASMD" or "CTX" are anchored to their full disease names
# and don't pull in unrelated hits.
#
# Notes on overlaps (kept as separate labels because the user listed them so):
#   - "Hunter disease" == Mucopolysaccharidosis Type 2 (MPS II)
#   - "Alpha Galactosidase" / "Fabry Disease" -> same enzyme/disease
#   - "Sphingomyelinase" / "ASMD" / "Niemann-Pick" (types A/B) overlap
#   - "X-linked hypophosphatemia" is a specific form of "Hypophosphatemic Rickets"
#   - "Cystinosis" appears twice in the source list; de-duplicated here.

DISEASE_SYNONYMS: dict[str, list[str]] = {
    "Adenosine Deaminase Deficiency": [
        "adenosine deaminase deficiency", "ADA-SCID", "ADA deficiency",
    ],
    "Familial Hypercholesterolemia": [
        "familial hypercholesterolemia", "familial hypercholesterolaemia",
    ],
    "Familial Mediterranean Fever": [
        "familial Mediterranean fever", "FMF",
    ],
    "Achondroplasia": ["achondroplasia"],
    "Alagille Syndrome": ["Alagille syndrome", "Alagille's syndrome"],
    "ASMD": [
        "acid sphingomyelinase deficiency", "ASMD",
    ],
    "CLN2": [
        "CLN2 disease", "neuronal ceroid lipofuscinosis type 2",
        "tripeptidyl peptidase 1 deficiency", "TPP1 deficiency",
    ],
    "CSID": [
        "congenital sucrase-isomaltase deficiency", "sucrase-isomaltase deficiency",
    ],
    "CTX": [
        "cerebrotendinous xanthomatosis",
    ],
    "Fabry Disease": [
        "Fabry disease", "Anderson-Fabry disease",
    ],
    "Gaucher Disease": ["Gaucher disease"],
    "Hyperinsulinemic Hypoglycemia": [
        "hyperinsulinemic hypoglycemia", "hyperinsulinaemic hypoglycaemia",
        "congenital hyperinsulinism",
    ],
    "Hypophosphatemic Rickets": [
        "hypophosphatemic rickets", "hypophosphataemic rickets",
    ],
    "Leptin Deficiency": [
        "leptin deficiency", "congenital leptin deficiency",
    ],
    "Lipodystrophy": [
        "lipodystrophy", "lipoatrophy",
    ],
    "Lysosomal Storage Diseases Panel": [
        "lysosomal storage disease", "lysosomal storage disorder",
    ],
    "Mucopolysaccharidosis Type 1": [
        "mucopolysaccharidosis type I", "mucopolysaccharidosis type 1",
        "MPS I", "Hurler syndrome", "Hurler-Scheie", "Scheie syndrome",
    ],
    "Mucopolysaccharidosis Type 4A": [
        "mucopolysaccharidosis type IVA", "mucopolysaccharidosis type 4A",
        "MPS IVA", "Morquio A",
    ],
    "Mucopolysaccharidosis Type 2": [
        "mucopolysaccharidosis type II", "mucopolysaccharidosis type 2",
        "MPS II", "Hunter syndrome",
    ],
    "Mucopolysaccharidosis Type 6": [
        "mucopolysaccharidosis type VI", "mucopolysaccharidosis type 6",
        "MPS VI", "Maroteaux-Lamy syndrome",
    ],
    "Niemann-Pick Disease": [
        "Niemann-Pick disease", "Niemann Pick disease",
    ],
    "Neuromuscular Diseases": [
        "neuromuscular disease", "neuromuscular disorder",
    ],
    "Progressive Familial Intrahepatic Cholestasis": [
        "progressive familial intrahepatic cholestasis", "PFIC",
    ],
    "PI3Kdelta Syndrome": [
        "activated PI3K delta syndrome", "APDS",
        "PI3K delta syndrome", "PI3Kdelta syndrome",
    ],
    "Pompe Disease": [
        "Pompe disease", "acid maltase deficiency",
        "glycogen storage disease type II", "glycogen storage disease type 2",
    ],
    "Cystinosis": ["cystinosis"],
    "Wilson Disease": [
        "Wilson disease", "Wilson's disease", "hepatolenticular degeneration",
    ],
    "Alpha Galactosidase": [
        "alpha-galactosidase A deficiency", "alpha galactosidase A deficiency",
    ],
    "X-linked Hypophosphatemia": [
        "X-linked hypophosphatemia", "X-linked hypophosphataemia", "XLH",
    ],
    "Sphingomyelinase": [
        "sphingomyelinase deficiency", "acid sphingomyelinase",
    ],
    "Hunter Disease": [
        "Hunter syndrome", "Hunter disease",
        "mucopolysaccharidosis type II", "MPS II",
    ],
    "Transthyretin Amyloidosis": [
        "transthyretin amyloidosis", "ATTR amyloidosis",
        "hereditary transthyretin amyloidosis", "hATTR",
    ],
    "Lung Adenocarcinoma": [
        "lung adenocarcinoma", "pulmonary adenocarcinoma",
        "adenocarcinoma of the lung", "LUAD",
    ],
}


# ---------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------

@dataclass
class ArticleMetadata:
    pmid: str = ""
    pmcid: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: str = ""
    doi: str = ""
    license: str = ""
    mesh_terms: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    diseases: list[str] = field(default_factory=list)
    article_type: str = ""  # "review", "case_report", or "review;case_report"
    is_open_access: bool = False


@dataclass
class ClinicalCase:
    case_id: str = ""
    pmcid: str = ""
    diseases: list[str] = field(default_factory=list)
    article_type: str = ""
    section: str = ""  # which body section this text came from (e.g. "case", "fulltext")
    case_text: str = ""
    abstract: str = ""


@dataclass
class CaseImage:
    image_id: str = ""
    case_id: str = ""
    pmcid: str = ""
    filename: str = ""
    caption: str = ""
    url: str = ""
    local_path: str = ""


# ---------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------

def configure_entrez(email: str, api_key: Optional[str] = None) -> float:
    """Configure Entrez and return the appropriate sleep interval."""
    Entrez.email = email
    Entrez.max_tries = 5
    Entrez.sleep_between_tries = 15

    if api_key:
        Entrez.api_key = api_key
        return NCBI_RATE_LIMIT_WITH_KEY

    return NCBI_RATE_LIMIT_NO_KEY


def safe_json_dump(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def normalize_pmc_oa_href(href: str) -> str:
    """Normalize PMC OA href values, including ftp and relative paths."""
    href = (href or "").strip()
    if href.startswith("ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/"):
        return href.replace("ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/", PMC_FTP_BASE, 1)
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(PMC_FTP_BASE, href)


def pmc_download_candidates(url: str) -> list[str]:
    """
    Return candidate PMC FTP URLs.

    Since April 13, 2026, legacy PMC FTP files may live under:
      /pub/pmc/deprecated/
    while OA service links may still point to:
      /pub/pmc/
    """
    candidates = [url]

    marker = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/"
    deprecated_marker = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/"

    if url.startswith(marker) and not url.startswith(deprecated_marker):
        candidates.append(url.replace(marker, deprecated_marker, 1))

    # Deduplicate while preserving order.
    return list(dict.fromkeys(candidates))


def is_valid_pdf(path: str | Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except Exception:
        return False


def stream_download(url: str, path: str | Path, timeout: int = 120, user_agent: str = DEFAULT_USER_AGENT) -> bool:
    """Stream-download a file and return True if a non-empty file is written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(
            url,
            timeout=timeout,
            stream=True,
            headers={"User-Agent": user_agent},
        ) as resp:
            if resp.status_code != 200:
                logger.warning("Download HTTP %s: %s", resp.status_code, url)
                return False

            with open(path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        return path.exists() and path.stat().st_size > 0

    except Exception as e:
        logger.warning("Download failed: %s -> %s", url, e)
        return False


# ---------------------------------------------------------------------
# Stage 1: PubMed Search
# ---------------------------------------------------------------------

def build_disease_query(
    disease_terms: list[str],
    article_types: list[str],
    use_pmc_oa_filter: bool = True,
) -> str:
    """Build a PubMed query for one disease across the requested article types.

    article_types is a list of class keys from ARTICLE_TYPE_CLASSES
    (e.g. "review", "trial", "case_report", "guideline", "commentary").

    Each class contributes a clause OR-ing its exact [pt] tokens with its
    free-text [tiab] fallbacks; the per-class clauses are then OR-ed together.
    """
    # Disease term block: each synonym searched in title/abstract, OR-ed.
    disease_block = " OR ".join(f'"{t}"[tiab]' for t in disease_terms)
    disease_block = f"({disease_block})"

    type_clauses: list[str] = []
    for atype in article_types:
        spec = ARTICLE_TYPE_CLASSES.get(atype)
        if spec is None:
            logger.warning("Unknown article-type class '%s'; skipping.", atype)
            continue
        parts = [f'"{t}"[pt]' for t in spec["pt"]]
        parts += [f'"{t}"[tiab]' for t in spec["tiab"]]
        if parts:
            type_clauses.append("(" + " OR ".join(parts) + ")")

    if not type_clauses:
        raise ValueError("At least one valid article type must be requested")

    type_block = "(" + " OR ".join(type_clauses) + ")"

    # Access filter: PMC OA subset (better PDF/package availability) or
    # broader free-full-text.
    # Access filter. Both are valid PubMed [sb] subset tokens:
    #   "pubmed pmc open access"[sb] -> the PMC Open Access Subset (liberal reuse
    #       license; best when you intend to redistribute the dataset).
    #   "pubmed pmc"[sb]             -> any article with free full text in PMC
    #       (broader; better recall, includes non-OA-licensed free articles).
    # NOTE: '"open access"[filter]' is NOT valid in the pubmed database and
    # silently matches nothing, so do not use it here.
    access_filter = '"pubmed pmc open access"[sb]' if use_pmc_oa_filter else '"pubmed pmc"[sb]'
    date_range = '("1990/01/01"[PDAT] : "3000/12/31"[PDAT])'

    query = f"{disease_block} AND {type_block} AND {access_filter} AND {date_range}"
    return query


def search_one_query(
    query: str,
    sleep_interval: float,
    max_results: int,
) -> list[str]:
    """Run a single PubMed query and return up to max_results PMIDs."""
    try:
        with Entrez.esearch(db="pubmed", term=query, retmax=0) as handle:
            record = Entrez.read(handle)
    except Exception as e:
        logger.error("PubMed count query failed: %s", e)
        return []

    total_count = int(record.get("Count", 0))
    if total_count == 0:
        return []

    fetch_count = min(total_count, max_results)
    batch_size = 9999
    pmids: list[str] = []

    for start in range(0, fetch_count, batch_size):
        batch = min(batch_size, fetch_count - start)
        try:
            with Entrez.esearch(
                db="pubmed",
                term=query,
                retstart=start,
                retmax=batch,
                sort="pub_date",  # stable ordering for paginated retrieval
            ) as handle:
                record = Entrez.read(handle)
            pmids.extend(str(x) for x in record.get("IdList", []))
        except Exception as e:
            logger.warning("PMID search batch failed at retstart=%s: %s", start, e)
        time.sleep(sleep_interval)

    # Deduplicate while preserving order (relevance/pub_date paging can repeat).
    return list(dict.fromkeys(pmids))


def search_pubmed_by_disease(
    diseases: dict[str, list[str]],
    article_types: list[str],
    email: str,
    api_key: Optional[str] = None,
    max_per_disease: int = 500,
    use_pmc_oa_filter: bool = True,
    should_stop: Optional[Callable[[], bool]] = None,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Search PubMed for each disease and article type.

    `should_stop`, if provided, is polled between disease searches; when it
    returns True the search ends early and returns whatever has been collected.

    Returns:
        all_pmids: de-duplicated list of every PMID found.
        provenance: {pmid: {"diseases": set-as-list, "article_types": set-as-list}}
    """
    stop = should_stop or (lambda: False)
    sleep_interval = configure_entrez(email, api_key)

    # Track per-PMID provenance as sets, materialized to lists at the end.
    prov_disease: dict[str, set[str]] = {}
    prov_type: dict[str, set[str]] = {}

    for disease_label, synonyms in tqdm(diseases.items(), desc="Searching diseases"):
        if stop():
            logger.warning("Stop requested; ending disease search early.")
            break
        for atype in article_types:
            query = build_disease_query(
                disease_terms=synonyms,
                article_types=[atype],
                use_pmc_oa_filter=use_pmc_oa_filter,
            )
            logger.info("[%s | %s] query: %s", disease_label, atype, query)
            pmids = search_one_query(query, sleep_interval, max_per_disease)
            logger.info("[%s | %s] -> %s PMIDs", disease_label, atype, len(pmids))

            for pmid in pmids:
                prov_disease.setdefault(pmid, set()).add(disease_label)
                prov_type.setdefault(pmid, set()).add(atype)

    all_pmids = list(prov_disease.keys())
    provenance: dict[str, dict[str, Any]] = {
        pmid: {
            "diseases": sorted(prov_disease.get(pmid, set())),
            "article_types": sorted(prov_type.get(pmid, set())),
        }
        for pmid in all_pmids
    }

    logger.info("Total unique PMIDs across all diseases: %s", len(all_pmids))
    return all_pmids, provenance


# ---------------------------------------------------------------------
# Stage 2: PMID -> PMCID Mapping
# ---------------------------------------------------------------------

def map_pmid_to_pmcid(pmids: list[str], email: str, api_key: Optional[str] = None) -> dict[str, str]:
    """Map PMIDs to PMCIDs using PubMed XML metadata."""
    sleep_interval = configure_entrez(email, api_key)
    pmid_to_pmcid: dict[str, str] = {}

    if not pmids:
        return pmid_to_pmcid

    batch_size = 200
    for i in tqdm(range(0, len(pmids), batch_size), desc="Mapping PMID->PMCID"):
        batch = pmids[i : i + batch_size]

        try:
            with Entrez.efetch(db="pubmed", id=",".join(batch), rettype="xml") as handle:
                records = Entrez.read(handle)

            for article in records.get("PubmedArticle", []):
                medline = article.get("MedlineCitation", {})
                pmid = str(medline.get("PMID", ""))

                pubmed_data = article.get("PubmedData", {})
                article_ids = pubmed_data.get("ArticleIdList", [])

                for aid in article_ids:
                    id_type = str(aid.attributes.get("IdType", ""))
                    if id_type == "pmc":
                        pmcid = str(aid)
                        if not pmcid.startswith("PMC"):
                            pmcid = f"PMC{pmcid}"
                        pmid_to_pmcid[pmid] = pmcid
                        break

        except Exception as e:
            logger.warning("PMID->PMCID batch failed at index %s: %s", i, e)

        time.sleep(sleep_interval)

    logger.info("Mapped %s / %s PMIDs to PMCIDs", len(pmid_to_pmcid), len(pmids))
    return pmid_to_pmcid


# ---------------------------------------------------------------------
# Stage 3: Fetch Full Text via BioC API
# ---------------------------------------------------------------------

def normalize_bioc_response(data: Any) -> dict[str, list[dict[str, Any]]]:
    """Normalize BioC JSON API variants into {'documents': [...]} shape."""
    if isinstance(data, list):
        all_docs: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if "passages" in item:
                all_docs.append(item)
            elif "documents" in item and isinstance(item["documents"], list):
                for doc in item["documents"]:
                    if isinstance(doc, dict):
                        all_docs.append(doc)
        return {"documents": all_docs}

    if isinstance(data, dict):
        if "documents" in data:
            docs = data.get("documents", [])
            flat_docs: list[dict[str, Any]] = []
            if isinstance(docs, list):
                for d in docs:
                    if isinstance(d, list):
                        flat_docs.extend(x for x in d if isinstance(x, dict))
                    elif isinstance(d, dict):
                        flat_docs.append(d)
            return {"documents": flat_docs}

        if "passages" in data:
            return {"documents": [data]}

    return {"documents": []}


def fetch_bioc_article(pmcid: str, user_agent: str = DEFAULT_USER_AGENT) -> Optional[dict[str, Any]]:
    """Fetch article content from the NCBI BioC API for PMC in JSON format."""
    url = f"{BIOC_BASE_URL}/BioC_json/{pmcid}/unicode"

    try:
        resp = requests.get(url, timeout=60, headers={"User-Agent": user_agent})
        if resp.status_code != 200:
            logger.debug("BioC fetch failed for %s: HTTP %s", pmcid, resp.status_code)
            return None

        return normalize_bioc_response(resp.json())

    except Exception as e:
        logger.debug("BioC fetch error for %s: %s", pmcid, e)
        return None


def fetch_article_metadata_pubmed(
    pmid: str,
    email: str,
    api_key: Optional[str] = None,
) -> ArticleMetadata:
    """Fetch detailed metadata from PubMed XML."""
    configure_entrez(email, api_key)
    meta = ArticleMetadata(pmid=pmid)

    try:
        with Entrez.efetch(db="pubmed", id=pmid, rettype="xml") as handle:
            records = Entrez.read(handle)

        articles = records.get("PubmedArticle", [])
        if not articles:
            return meta

        article = articles[0]
        medline = article.get("MedlineCitation", {})
        art_data = medline.get("Article", {})

        meta.title = str(art_data.get("ArticleTitle", ""))

        for author in art_data.get("AuthorList", []):
            last = author.get("LastName", "")
            first = author.get("ForeName", "")
            if last:
                meta.authors.append(f"{first} {last}".strip())

        journal = art_data.get("Journal", {})
        meta.journal = str(journal.get("Title", ""))
        pub_date = journal.get("JournalIssue", {}).get("PubDate", {})
        meta.year = str(pub_date.get("Year", ""))

        for eid in art_data.get("ELocationID", []):
            if str(eid.attributes.get("EIdType", "")) == "doi":
                meta.doi = str(eid)

        for mesh in medline.get("MeshHeadingList", []):
            descriptor = mesh.get("DescriptorName", "")
            if descriptor:
                meta.mesh_terms.append(str(descriptor))

        for kw_list in medline.get("KeywordList", []):
            for kw in kw_list:
                meta.keywords.append(str(kw))

        # Classify article type from PubMed publication types.
        pub_types = {
            str(pt).lower()
            for pt in art_data.get("PublicationTypeList", [])
        }
        meta.article_type = ";".join(classify_publication_types(pub_types))

    except Exception as e:
        logger.warning("Metadata fetch failed for PMID %s: %s", pmid, e)

    return meta


# ---------------------------------------------------------------------
# Stage 4: Extract case narratives / full text from BioC Content
# ---------------------------------------------------------------------

# Section titles that mark the start of a case narrative in human case reports.
CASE_SECTION_PATTERNS = [
    r"case\s*(report|presentation|description|history|summary|study)",
    r"clinical\s*(case|presentation|history|findings|summary|course)",
    r"patient\s*(history|presentation|case|report)",
    r"case$",
    r"^case\b",
]
CASE_SECTION_RE = re.compile("|".join(CASE_SECTION_PATTERNS), re.IGNORECASE)

# Section titles to exclude from being treated as the body of a case narrative.
NON_BODY_SECTION_RE = re.compile(
    r"^(references?|acknowledg|funding|conflict|author contribution|"
    r"supplementary|abbreviation|competing interest)",
    re.IGNORECASE,
)


def flatten_passages(doc: dict[str, Any]) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    raw_passages = doc.get("passages", [])
    if not isinstance(raw_passages, list):
        return passages

    for p in raw_passages:
        if isinstance(p, dict):
            passages.append(p)
        elif isinstance(p, list):
            passages.extend(item for item in p if isinstance(item, dict))
    return passages


def is_title_passage(passage: dict[str, Any]) -> bool:
    infons = passage.get("infons", {})
    if not isinstance(infons, dict):
        infons = {}
    ptype = str(infons.get("type", "")).lower()
    section_type = str(infons.get("section_type", "")).lower()
    return ptype.startswith("title") or section_type in {"title", "section_title"}


def is_abstract_passage(passage: dict[str, Any]) -> bool:
    infons = passage.get("infons", {})
    if not isinstance(infons, dict):
        infons = {}
    ptype = str(infons.get("type", "")).lower()
    section_type = str(infons.get("section_type", "")).lower()
    return section_type == "abstract" or ptype == "abstract"


def extract_text_from_bioc(
    bioc_data: dict[str, Any],
    pmcid: str,
    diseases: list[str],
    article_type: str,
) -> list[ClinicalCase]:
    """Extract narrative text from BioC JSON.

    For case reports, segment out the case-narrative section(s). For reviews
    (or anything else), capture the full body text. Always capture the abstract.
    The returned ClinicalCase records carry disease + article_type provenance.
    """
    is_case_report = any(
        ARTICLE_TYPE_CLASSES.get(k, {}).get("narrative", False)
        for k in (article_type or "").split(";")
        if k
    )

    case_texts: list[tuple[str, str]] = []  # (body_text, abstract)
    body_section = "case" if is_case_report else "fulltext"

    try:
        for doc in bioc_data.get("documents", []):
            if not isinstance(doc, dict):
                continue

            passages = flatten_passages(doc)
            abstract_parts: list[str] = []
            body_parts: list[str] = []          # full body (used for reviews / fallback)
            current_case_parts: list[str] = []   # active case-narrative buffer
            in_case_section = False

            for passage in passages:
                text = str(passage.get("text", "") or "").strip()
                if not text:
                    continue

                if is_abstract_passage(passage):
                    abstract_parts.append(text)
                    continue

                if is_title_passage(passage):
                    if NON_BODY_SECTION_RE.search(text):
                        # Stop collecting case narrative once we hit refs/etc.
                        if in_case_section and current_case_parts:
                            case_texts.append(
                                (" ".join(current_case_parts), " ".join(abstract_parts))
                            )
                            current_case_parts = []
                        in_case_section = False
                        continue

                    if is_case_report and CASE_SECTION_RE.search(text):
                        if current_case_parts:
                            case_texts.append(
                                (" ".join(current_case_parts), " ".join(abstract_parts))
                            )
                            current_case_parts = []
                        in_case_section = True
                        continue

                    if in_case_section:
                        # A new non-case section closes the current case.
                        if current_case_parts:
                            case_texts.append(
                                (" ".join(current_case_parts), " ".join(abstract_parts))
                            )
                            current_case_parts = []
                        in_case_section = False

                # Body text accumulation.
                if not NON_BODY_SECTION_RE.search(text):
                    body_parts.append(text)
                if in_case_section:
                    current_case_parts.append(text)

            if current_case_parts:
                case_texts.append(
                    (" ".join(current_case_parts), " ".join(abstract_parts))
                )

            # If this is not a case report (or no case section was found),
            # fall back to the full body text for this document.
            if not is_case_report or not case_texts:
                full_abstract = " ".join(x.strip() for x in abstract_parts if x.strip())
                full_body = " ".join(x.strip() for x in body_parts if x.strip())
                chosen = full_body or full_abstract
                if chosen:
                    case_texts.append((chosen, full_abstract))
                    body_section = "fulltext" if full_body else "abstract"

    except Exception as e:
        logger.warning("Text extraction failed for %s: %s", pmcid, e)

    cases: list[ClinicalCase] = []
    for idx, (text, abstract) in enumerate(case_texts):
        text = " ".join(text.split())
        abstract = " ".join(abstract.split())
        if not text:
            continue

        cases.append(
            ClinicalCase(
                case_id=f"{pmcid}_{idx + 1:02d}",
                pmcid=pmcid,
                diseases=list(diseases),
                article_type=article_type,
                section=body_section,
                case_text=text,
                abstract=abstract,
            )
        )

    return cases


def extract_captions_from_bioc(bioc_data: dict[str, Any], pmcid: str) -> list[dict[str, str]]:
    captions: list[dict[str, str]] = []
    try:
        for doc in bioc_data.get("documents", []):
            if not isinstance(doc, dict):
                continue
            for passage in flatten_passages(doc):
                infons = passage.get("infons", {})
                if not isinstance(infons, dict):
                    infons = {}
                passage_type = str(infons.get("type", "")).lower()
                section_type = str(infons.get("section_type", "")).lower()
                if "caption" in passage_type or "fig" in passage_type or "caption" in section_type:
                    text = str(passage.get("text", "") or "").strip()
                    if text:
                        captions.append(
                            {
                                "pmcid": pmcid,
                                "figure_id": str(infons.get("id", "")),
                                "file_ref": str(infons.get("file", "")),
                                "caption": text,
                            }
                        )
    except Exception as e:
        logger.warning("Caption extraction failed for %s: %s", pmcid, e)

    return captions


# ---------------------------------------------------------------------
# Stage 5: PDF and Image Downloads
# ---------------------------------------------------------------------

def get_pmc_oa_links(pmcid: str, user_agent: str = DEFAULT_USER_AGENT) -> dict[str, list[str]]:
    """Query PMC OA service and return normalized links grouped by format."""
    url = f"{PMC_OA_SERVICE_URL}?id={pmcid}"
    links: dict[str, list[str]] = {"pdf": [], "tgz": [], "other": []}

    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": user_agent})
        if resp.status_code != 200:
            logger.warning("OA lookup HTTP %s for %s", resp.status_code, pmcid)
            return links

        root = ET.fromstring(resp.content)
        error_node = root.find(".//error")
        if error_node is not None:
            logger.warning("OA lookup error for %s: %s", pmcid, error_node.text)
            return links

        for link in root.iter("link"):
            fmt = (link.get("format") or "").lower().strip()
            href = link.get("href") or ""
            if not href:
                continue
            normalized = normalize_pmc_oa_href(href)

            if fmt == "pdf":
                links["pdf"].append(normalized)
            elif fmt in {"tgz", "tar.gz"}:
                links["tgz"].append(normalized)
            else:
                links["other"].append(normalized)

    except Exception as e:
        logger.warning("OA service lookup failed for %s: %s", pmcid, e)

    return links


def get_pmc_license_and_oa(pmcid: str, user_agent: str = DEFAULT_USER_AGENT) -> tuple[str, bool]:
    """Fetch (license, is_open_access) for a PMC article from the OA service.

    The PMC OA service only returns a <record> for articles that are in the
    PMC Open Access Subset; non-OA articles yield an <error> (or no record).
    So the presence of a <record> is a reliable open-access signal. The
    <record> 'license' attribute (e.g. 'CC BY', 'CC BY-NC') is returned when
    present. Returns ("", False) on lookup failure or when not in the subset.
    """
    url = f"{PMC_OA_SERVICE_URL}?id={pmcid}"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": user_agent})
        if resp.status_code != 200:
            return "", False
        root = ET.fromstring(resp.content)
        record = root.find(".//record")
        if record is not None:
            return (record.get("license") or "").strip(), True
    except Exception as e:
        logger.debug("License/OA lookup failed for %s: %s", pmcid, e)
    return "", False


def download_pdf(pmcid: str, save_dir: str, user_agent: str = DEFAULT_USER_AGENT) -> Optional[str]:
    """Download article PDF from PMC OA service when a PDF exists."""
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{pmcid}.pdf")

    if os.path.exists(save_path) and is_valid_pdf(save_path):
        logger.info("PDF already exists: %s", save_path)
        return save_path

    if os.path.exists(save_path):
        logger.warning("Removing invalid existing PDF: %s", save_path)
        os.remove(save_path)

    links = get_pmc_oa_links(pmcid, user_agent=user_agent)
    pdf_urls = links.get("pdf", [])
    tgz_urls = links.get("tgz", [])

    logger.info("%s: OA links found | pdf=%s tgz=%s", pmcid, len(pdf_urls), len(tgz_urls))

    # Direct PDF first.
    for pdf_url in pdf_urls:
        for candidate_url in pmc_download_candidates(pdf_url):
            if stream_download(candidate_url, save_path, timeout=120, user_agent=user_agent) and is_valid_pdf(save_path):
                logger.info("Downloaded direct PDF for %s", pmcid)
                return save_path

            logger.warning("Direct PDF failed or invalid for %s: %s", pmcid, candidate_url)
            if os.path.exists(save_path):
                os.remove(save_path)

    # Fall back to TGZ package and extract largest PDF.
    if not tgz_urls:
        logger.warning("No PDF or TGZ OA link available for %s", pmcid)
        return None

    for tgz_url in tgz_urls:
        tgz_path = os.path.join(save_dir, f"{pmcid}.tar.gz")

        downloaded_tgz = False
        for candidate_url in pmc_download_candidates(tgz_url):
            if stream_download(candidate_url, tgz_path, timeout=180, user_agent=user_agent):
                downloaded_tgz = True
                break
            if os.path.exists(tgz_path):
                os.remove(tgz_path)

        if not downloaded_tgz:
            continue

        try:
            with tarfile.open(tgz_path, "r:gz") as tar:
                pdf_members = [
                    m for m in tar.getmembers()
                    if m.isfile() and m.name.lower().endswith(".pdf")
                ]

                if not pdf_members:
                    logger.warning("No PDF inside OA package for %s", pmcid)
                    continue

                pdf_member = max(pdf_members, key=lambda m: m.size)
                pdf_file = tar.extractfile(pdf_member)
                if not pdf_file:
                    logger.warning("Could not extract PDF member for %s: %s", pmcid, pdf_member.name)
                    continue

                with open(save_path, "wb") as f:
                    f.write(pdf_file.read())

                if is_valid_pdf(save_path):
                    logger.info("Extracted PDF for %s: %s", pmcid, pdf_member.name)
                    return save_path

                logger.warning("Extracted file is not a valid PDF for %s: %s", pmcid, pdf_member.name)
                if os.path.exists(save_path):
                    os.remove(save_path)

        except Exception as e:
            logger.warning("TGZ extraction failed for %s: %s", pmcid, e)

        finally:
            if os.path.exists(tgz_path):
                os.remove(tgz_path)

    return None


def get_image_urls_from_europepmc(pmcid: str, user_agent: str = DEFAULT_USER_AGENT) -> list[dict[str, str]]:
    """Discover figure image URLs from Europe PMC fullTextXML."""
    images: list[dict[str, str]] = []
    pmc_num = pmcid.replace("PMC", "")
    fig_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC/{pmc_num}/fullTextXML"

    try:
        resp = requests.get(fig_url, timeout=30, headers={"User-Agent": user_agent})
        if resp.status_code != 200:
            logger.debug("Europe PMC XML HTTP %s for %s", resp.status_code, pmcid)
            return images

        soup = BeautifulSoup(resp.content, "lxml-xml")
        for graphic in soup.find_all("graphic"):
            href = graphic.get("xlink:href", "") or graphic.get("href", "")
            if not href:
                continue
            img_url = f"https://europepmc.org/articles/{pmcid}/bin/{href}"
            if not any(href.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"]):
                img_url += ".jpg"
            images.append({"pmcid": pmcid, "filename": href, "url": img_url})

    except Exception as e:
        logger.debug("Image URL fetch failed for %s: %s", pmcid, e)

    return images


def download_image(url: str, save_path: str, user_agent: str = DEFAULT_USER_AGENT) -> bool:
    return stream_download(url, save_path, timeout=60, user_agent=user_agent)



# ---------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------

def save_dataframe(df: pd.DataFrame, path: Path, also_csv: bool = False) -> None:
    """Save parquet, with clear pyarrow error reporting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(path, index=False)
    except Exception as e:
        logger.error("Could not save parquet %s: %s", path, e)
        csv_path = path.with_suffix(".csv")
        logger.warning("Saving CSV fallback instead: %s", csv_path)
        df.to_csv(csv_path, index=False)
        return

    if also_csv:
        df.to_csv(path.with_suffix(".csv"), index=False)


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_txt_summary(rows: list[dict[str, Any]], path: Path) -> None:
    """Write a human-readable TXT summary, one block per publication.

    For each publication it reports: PDF file name, article name,
    whether it is open access, and whether the PDF was downloaded.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    def yn(value: bool) -> str:
        return "Yes" if value else "No"

    n = len(rows)
    n_oa = sum(1 for r in rows if r.get("is_open_access"))
    n_pdf = sum(1 for r in rows if r.get("pdf_downloaded"))
    any_requested = any(r.get("pdf_requested") for r in rows)

    with open(path, "w", encoding="utf-8") as f:
        f.write("RareDx Publication Summary\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total publications: {n}\n")
        f.write(f"Open access:        {n_oa}\n")
        if any_requested:
            f.write(f"PDFs downloaded:    {n_pdf}\n")
        else:
            f.write("PDFs downloaded:    (PDF download not requested)\n")
        f.write("=" * 60 + "\n\n")

        for i, r in enumerate(rows, 1):
            if r.get("pdf_requested"):
                pdf_status = yn(r.get("pdf_downloaded", False))
                pdf_name = r.get("pdf_filename") or "(none)"
            else:
                pdf_status = "Not requested"
                pdf_name = "(none)"

            f.write(f"[{i}] {r.get('pmcid', '')}\n")
            f.write(f"    PDF file name:    {pdf_name}\n")
            f.write(f"    Article name:     {r.get('title', '')}\n")
            f.write(f"    Is Open Access:   {yn(r.get('is_open_access', False))}\n")
            f.write(f"    Is PDF downloaded: {pdf_status}\n")
            f.write("\n")

    logger.info("Wrote TXT summary: %s", path)


# ---------------------------------------------------------------------
# Stage 8: PDF → Markdown conversion
# ---------------------------------------------------------------------

def convert_pdfs_to_markdown(
    pdf_dir: Path,
    md_dir: Path,
    should_stop: Optional[Callable[[], bool]] = None,
) -> int:
    """Convert downloaded PDFs to Markdown using pymupdf4llm.

    Returns the number of Markdown files successfully written.
    Already-converted files are skipped.
    """
    try:
        import pymupdf4llm
    except ImportError:
        logger.error(
            "pymupdf4llm is not installed. Run: pip install pymupdf4llm"
        )
        return 0

    stop = should_stop or (lambda: False)

    if not pdf_dir.exists():
        logger.warning("PDF directory does not exist: %s", pdf_dir)
        return 0

    md_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        logger.info("No PDF files found in %s.", pdf_dir)
        return 0

    converted = 0
    logger.info("Converting %d PDFs to Markdown → %s", len(pdf_files), md_dir)

    for pdf_path in pdf_files:
        if stop():
            logger.warning("Stop requested; ending Markdown conversion early.")
            break

        out_path = md_dir / (pdf_path.stem + ".md")
        if out_path.exists():
            logger.debug("Markdown already exists, skipping: %s", out_path.name)
            converted += 1
            continue

        try:
            md_text = pymupdf4llm.to_markdown(str(pdf_path))
            out_path.write_text(md_text, encoding="utf-8")
            logger.info("Converted: %s", pdf_path.name)
            converted += 1
        except Exception as e:
            logger.warning("Failed to convert %s: %s", pdf_path.name, e)

    logger.info(
        "Markdown conversion complete: %d / %d files.", converted, len(pdf_files)
    )
    return converted


# ---------------------------------------------------------------------
# Stage 9: BioC / Markdown -> FAISS RAG vector database
# ---------------------------------------------------------------------

RAG_SOURCE_OPTIONS = {
    "bioc": "BioC JSON (recommended)",
    "markdown": "PDF Markdown",
    "hybrid": "Hybrid BioC + PDF Markdown",
}
DEFAULT_RAG_SOURCE = "bioc"

# Curated embedding models offered by default for the BioC/FAISS RAG index.
# Key = HuggingFace model repo ID, value = short UI label. This is a starting
# menu, not a hard limit: any sentence-transformers-compatible HuggingFace
# model can be used (see list_cached_embedding_models / normalize_hf_model_id
# below and the "Add a custom HuggingFace embedding model" UI control).
EMBEDDING_MODELS: dict[str, str] = {
    "BAAI/bge-small-en-v1.5": "bge-small · fast, general (default)",
    "BAAI/bge-base-en-v1.5": "bge-base · higher quality, general",
    "BAAI/bge-large-en-v1.5": "bge-large · highest quality, general (slower)",
    "pritamdeka/S-PubMedBert-MS-MARCO": "PubMedBERT (MS-MARCO) · biomedical-domain",
}
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
BIOC_EMBEDDING_SHORT_NAMES = {
    "bge-small": "BAAI/bge-small-en-v1.5",
    "bge-base": "BAAI/bge-base-en-v1.5",
    "bge-large": "BAAI/bge-large-en-v1.5",
    "pubmedbert": "pritamdeka/S-PubMedBert-MS-MARCO",
}

# Written inside each vector_db/ folder so the chatbot loads the SAME embedding
# model that built the index (a mismatch silently degrades retrieval), and so
# the chunk size/overlap and RAG source that built it are recorded for later
# inspection/reproduction — chunking has no stored effect on how the index is
# loaded, only on what was embedded when it was built.
EMBEDDING_CONFIG_FILENAME = "embedding_config.json"


def list_cached_embedding_models() -> list[str]:
    """Return HuggingFace model repo IDs already present in the local HF
    cache (~/.cache/huggingface/hub by default), best-effort. Used to mark
    which embedding models are already downloaded vs. will be fetched on
    first use. Returns [] if huggingface_hub isn't importable or the cache
    can't be read, rather than raising."""
    try:
        from huggingface_hub import scan_cache_dir

        cache = scan_cache_dir()
        return sorted({repo.repo_id for repo in cache.repos if repo.repo_type == "model"})
    except Exception:
        return []


def normalize_hf_model_id(raw: str) -> str | None:
    """Parse a pasted HuggingFace URL or bare 'org/model' string into a clean
    'org/model' repo ID, or None if it doesn't look like one. Accepts, e.g.:
    'BAAI/bge-small-en-v1.5', 'https://huggingface.co/BAAI/bge-small-en-v1.5',
    or 'https://huggingface.co/BAAI/bge-small-en-v1.5/tree/main'. Does not
    verify the repo exists or is sentence-transformers-compatible — that
    surfaces as a normal download error the first time it's used."""
    s = (raw or "").strip()
    if not s:
        return None
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^(www\.)?huggingface\.co/", "", s)
    s = s.split("?", 1)[0]
    parts = [p for p in s.split("/") if p]
    if len(parts) < 2:
        return None
    org, model = parts[0], parts[1]
    if not re.match(r"^[\w.\-]+$", org) or not re.match(r"^[\w.\-]+$", model):
        return None
    return f"{org}/{model}"


def resolve_embedding_model(value: str) -> str:
    """Resolve a CLI short name (e.g. 'bge-small') or a raw/URL-style
    HuggingFace reference into a clean embedding_model repo ID that
    HuggingFaceEmbeddings can load directly."""
    if value in BIOC_EMBEDDING_SHORT_NAMES:
        return BIOC_EMBEDDING_SHORT_NAMES[value]
    return normalize_hf_model_id(value) or value


def clean_rag_text(text: Any) -> str:
    """Normalize whitespace and common PDF/BioC artifacts for embedding."""
    text = str(text or "")
    text = text.replace("\u00ad", "")
    text = text.replace("\ufffe", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _xml_cell_text(cell: Any) -> str:
    """Extract readable text from an XML table cell, including nested xrefs."""
    parts: list[str] = []
    if cell.text:
        parts.append(cell.text)
    for child in list(cell):
        child_text = "".join(child.itertext()).strip()
        if child_text:
            parts.append(child_text)
        if child.tail:
            parts.append(child.tail)
    return clean_rag_text(" ".join(parts))


def bioc_table_xml_to_markdown(xml_text: str) -> str:
    """Convert a BioC/JATS table XML payload to a compact Markdown table.

    Falls back to an empty string when XML parsing fails. The flat BioC `text`
    field is still retained by the caller, so failures are non-destructive.
    """
    xml_text = str(xml_text or "").strip()
    if not xml_text:
        return ""

    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return ""

    def rows_from(parent_name: str) -> list[list[str]]:
        parent = root.find(f".//{parent_name}")
        if parent is None:
            return []
        rows: list[list[str]] = []
        for tr in parent.findall(".//tr"):
            cells = [_xml_cell_text(c) for c in list(tr) if c.tag in {"th", "td"}]
            if any(cells):
                rows.append(cells)
        return rows

    header_rows = rows_from("thead")
    body_rows = rows_from("tbody")
    if not header_rows and not body_rows:
        return ""

    if header_rows:
        header = header_rows[0]
        body = body_rows
    else:
        width = max(len(r) for r in body_rows)
        header = [f"Column {i + 1}" for i in range(width)]
        body = body_rows

    width = max([len(header)] + [len(r) for r in body] or [len(header)])
    header = header + [""] * (width - len(header))
    normalized_body = [r + [""] * (width - len(r)) for r in body]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in normalized_body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _bioc_chunk_kind(section_type: str, passage_type: str) -> str:
    section = section_type.upper()
    ptype = passage_type.lower()
    if section == "ABSTRACT":
        return "abstract"
    if section == "TITLE":
        return "title"
    if section == "TABLE":
        if "caption" in ptype:
            return "table_caption"
        if "footnote" in ptype:
            return "table_footnote"
        return "table"
    if section == "FIG":
        return "figure_caption"
    if section in {"REF", "REFERENCES"}:
        return "reference"
    return "section_text"


def bioc_json_to_documents(
    bioc_path: Path,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
    include_references: bool = False,
) -> list[Any]:
    """Create LangChain Documents directly from a BioC JSON article.

    BioC is preferred over PDF-derived Markdown because it preserves article
    identifiers, section labels, passage types, table XML, captions, and offsets.
    """
    try:
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:
        logger.error(
            "Missing RAG dependency: %s. Run: pip install langchain "
            "langchain-community langchain-huggingface faiss-cpu "
            "sentence-transformers langchain-text-splitters",
            exc,
        )
        return []

    try:
        data = json.loads(Path(bioc_path).read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read BioC JSON %s: %s", bioc_path, exc)
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    docs: list[Any] = []

    for article in data.get("documents", []):
        if not isinstance(article, dict):
            continue

        pmcid = str(article.get("id") or Path(bioc_path).stem)
        article_infons = article.get("infons") or {}
        article_license = str(article_infons.get("license", ""))
        passages = article.get("passages", [])
        if not isinstance(passages, list):
            continue

        title = ""
        current_h1 = ""
        current_h2 = ""
        current_h3 = ""
        table_context_by_id: dict[str, dict[str, str]] = {}

        for passage_index, passage in enumerate(passages):
            if not isinstance(passage, dict):
                continue

            infons = passage.get("infons") or {}
            section_type = str(infons.get("section_type", "")).upper()
            passage_type = str(infons.get("type", "")).lower()
            text = clean_rag_text(passage.get("text", ""))
            if not text:
                continue

            if section_type in {"REF", "REFERENCES"} and not include_references:
                continue

            if section_type == "TITLE" and not title:
                title = text

            if passage_type.startswith("title") and section_type not in {"ABSTRACT", "TABLE", "FIG"}:
                if passage_type == "title_1":
                    current_h1, current_h2, current_h3 = text, "", ""
                elif passage_type == "title_2":
                    current_h2, current_h3 = text, ""
                elif passage_type == "title_3":
                    current_h3 = text
                continue

            chunk_kind = _bioc_chunk_kind(section_type, passage_type)
            passage_id = str(infons.get("id", ""))
            file_name = str(infons.get("file", ""))

            heading_parts = [x for x in [current_h1, current_h2, current_h3] if x]
            heading = " > ".join(heading_parts) or section_type or "Article"

            if chunk_kind in {"table_caption", "table_footnote"} and passage_id:
                table_context_by_id.setdefault(passage_id, {})[chunk_kind] = text

            table_markdown = ""
            if chunk_kind == "table":
                table_markdown = bioc_table_xml_to_markdown(str(infons.get("xml", "")))
                caption = table_context_by_id.get(passage_id, {}).get("table_caption", "")
                footnote = table_context_by_id.get(passage_id, {}).get("table_footnote", "")
                content_text = "\n\n".join(
                    x for x in [
                        f"Table caption: {caption}" if caption else "",
                        table_markdown,
                        f"Flat table text: {text}",
                        f"Table footnote: {footnote}" if footnote else "",
                    ] if x
                )
            else:
                content_text = text

            front_matter = [
                f"PMCID: {pmcid}",
                f"Title: {title}" if title else "",
                f"Section: {section_type or 'UNKNOWN'}",
                f"Heading: {heading}",
                f"Passage type: {passage_type or 'unknown'}",
                f"Chunk kind: {chunk_kind}",
            ]
            enriched_text = "\n".join(x for x in front_matter if x) + "\n\n" + content_text

            for chunk_index, chunk in enumerate(splitter.split_text(enriched_text)):
                docs.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "source": Path(bioc_path).name,
                            "rag_source": "bioc",
                            "pmcid": pmcid,
                            "title": title,
                            "license": article_license,
                            "section_type": section_type,
                            "section": heading,
                            "passage_type": passage_type,
                            "chunk_kind": chunk_kind,
                            "passage_index": passage_index,
                            "chunk_id": chunk_index,
                            "offset": passage.get("offset", ""),
                            "file": file_name,
                            "id": passage_id,
                            "doi": infons.get("article-id_doi", ""),
                            "pmid": infons.get("article-id_pmid", ""),
                        },
                    )
                )

    return docs


def markdown_dir_to_documents(
    md_dir: Path,
    md_chunk_size: int = 1000,
    md_chunk_overlap: int = 100,
) -> list[Any]:
    """Create LangChain Documents from parsed Markdown files."""
    try:
        from langchain_text_splitters import (
            MarkdownHeaderTextSplitter,
            RecursiveCharacterTextSplitter,
        )
        from langchain_core.documents import Document
    except ImportError as exc:
        logger.error(
            "Missing RAG dependency: %s. Run: pip install langchain "
            "langchain-text-splitters",
            exc,
        )
        return []

    md_files = sorted(Path(md_dir).glob("*.md"))
    if not md_files:
        logger.warning("No Markdown files found in %s.", md_dir)
        return []

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=md_chunk_size,
        chunk_overlap=md_chunk_overlap,
    )

    all_docs: list[Any] = []
    for md_path in md_files:
        try:
            content = md_path.read_text(encoding="utf-8")
            sections = md_splitter.split_text(content)
            for section in sections:
                header_ctx = " > ".join(
                    v for k, v in section.metadata.items() if k.startswith("Header")
                )
                for i, chunk in enumerate(text_splitter.split_text(section.page_content)):
                    page_content = (
                        f"Context: {header_ctx}\n\n{chunk}" if header_ctx else chunk
                    )
                    all_docs.append(
                        Document(
                            page_content=page_content,
                            metadata={
                                "source": md_path.name,
                                "rag_source": "markdown",
                                "section": header_ctx,
                                "section_type": "PDF_MARKDOWN",
                                "chunk_kind": "pdf_markdown",
                                "chunk_id": i,
                            },
                        )
                    )
        except Exception as e:
            logger.warning("Failed to process %s for RAG: %s", md_path.name, e)

    return all_docs


def save_faiss_documents(
    docs: list[Any],
    vector_db_dir: Path,
    device: str = "cpu",
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    extra_config: dict[str, Any] | None = None,
) -> int:
    """Embed documents and persist a LangChain FAISS vector database.

    `extra_config`, if given, is merged into embedding_config.json alongside
    embedding_model — callers use it to record the RAG source and the
    chunk size/overlap that built this specific index (see build_rag_database*
    below), since none of that is otherwise recoverable from the index itself.
    """
    if not docs:
        logger.warning("No RAG documents were created.")
        return 0

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
    except ImportError as exc:
        logger.error(
            "Missing RAG dependency: %s. "
            "Run: pip install langchain langchain-community "
            "langchain-huggingface faiss-cpu sentence-transformers",
            exc,
        )
        return 0

    logger.info(
        "Total RAG chunks: %d. Initialising embedding model %s on %s ...",
        len(docs), embedding_model, device,
    )
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    logger.info("Building FAISS index ... (this may take several minutes)")
    vector_db_dir.mkdir(parents=True, exist_ok=True)
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(str(vector_db_dir))
    # Record which embedding model built this index so the chatbot can load a
    # matching one (a mismatch silently breaks retrieval), plus whatever
    # chunking/source details the caller supplied.
    config = {"embedding_model": embedding_model, "normalize_embeddings": True}
    if extra_config:
        config.update(extra_config)
    safe_json_dump(config, vector_db_dir / EMBEDDING_CONFIG_FILENAME)
    return len(docs)


def build_rag_database(
    md_dir: Path,
    vector_db_dir: Path,
    device: str = "cpu",
    md_chunk_size: int = 1000,
    md_chunk_overlap: int = 100,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> int:
    """Backward-compatible Markdown-only RAG builder."""
    logger.info(
        "Building Markdown RAG database from %s (chunk=%d chars, overlap=%d chars)",
        md_dir,
        md_chunk_size,
        md_chunk_overlap,
    )
    docs = markdown_dir_to_documents(md_dir, md_chunk_size, md_chunk_overlap)
    n = save_faiss_documents(
        docs, vector_db_dir, device=device, embedding_model=embedding_model,
        extra_config={
            "rag_source": "markdown",
            "md_chunk_size": md_chunk_size,
            "md_chunk_overlap": md_chunk_overlap,
        },
    )
    if n:
        logger.info("RAG database saved to %s (%d chunks)", vector_db_dir, n)
    return n


def build_rag_database_from_bioc(
    raw_bioc_dir: Path,
    vector_db_dir: Path,
    device: str = "cpu",
    bioc_chunk_size: int = 1200,
    bioc_chunk_overlap: int = 150,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> int:
    """Build a BioC-first FAISS RAG database from raw_bioc/*.json."""
    json_files = sorted(Path(raw_bioc_dir).glob("*.json"))
    if not json_files:
        logger.warning("No BioC JSON files found in %s.", raw_bioc_dir)
        return 0

    logger.info(
        "Building BioC RAG database from %d JSON files (chunk=%d chars, overlap=%d chars)",
        len(json_files),
        bioc_chunk_size,
        bioc_chunk_overlap,
    )
    all_docs: list[Any] = []
    for json_path in json_files:
        all_docs.extend(
            bioc_json_to_documents(
                json_path,
                chunk_size=bioc_chunk_size,
                chunk_overlap=bioc_chunk_overlap,
            )
        )

    n = save_faiss_documents(
        all_docs, vector_db_dir, device=device, embedding_model=embedding_model,
        extra_config={
            "rag_source": "bioc",
            "bioc_chunk_size": bioc_chunk_size,
            "bioc_chunk_overlap": bioc_chunk_overlap,
        },
    )
    if n:
        logger.info("BioC RAG database saved to %s (%d chunks)", vector_db_dir, n)
    return n


def build_hybrid_rag_database(
    raw_bioc_dir: Path,
    md_dir: Path,
    vector_db_dir: Path,
    device: str = "cpu",
    bioc_chunk_size: int = 1200,
    bioc_chunk_overlap: int = 150,
    md_chunk_size: int = 1000,
    md_chunk_overlap: int = 100,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> int:
    """Build a combined BioC + PDF-Markdown FAISS RAG database."""
    docs: list[Any] = []
    for json_path in sorted(Path(raw_bioc_dir).glob("*.json")):
        docs.extend(
            bioc_json_to_documents(
                json_path,
                chunk_size=bioc_chunk_size,
                chunk_overlap=bioc_chunk_overlap,
            )
        )
    docs.extend(markdown_dir_to_documents(md_dir, md_chunk_size, md_chunk_overlap))
    n = save_faiss_documents(
        docs, vector_db_dir, device=device, embedding_model=embedding_model,
        extra_config={
            "rag_source": "hybrid",
            "bioc_chunk_size": bioc_chunk_size,
            "bioc_chunk_overlap": bioc_chunk_overlap,
            "md_chunk_size": md_chunk_size,
            "md_chunk_overlap": md_chunk_overlap,
        },
    )
    if n:
        logger.info("Hybrid RAG database saved to %s (%d chunks)", vector_db_dir, n)
    return n


# ---------------------------------------------------------------------
# Main Pipeline Orchestrator
# ---------------------------------------------------------------------

def run_pipeline(
    email: str,
    diseases: dict[str, list[str]],
    article_types: list[str],
    api_key: Optional[str] = None,
    max_per_disease: int = 500,
    output_dir: str = "./raredx_data",
    download_images: bool = False,
    download_pdfs: bool = False,
    use_pmc_oa_filter: bool = True,
    save_raw_bioc: bool = True,
    user_agent: str = DEFAULT_USER_AGENT,
    should_stop: Optional[Callable[[], bool]] = None,
    convert_to_markdown: bool = False,
    build_rag: bool = False,
    rag_source: str = DEFAULT_RAG_SOURCE,
    rag_device: str = "cpu",
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    bioc_chunk_size: int = 1200,
    bioc_chunk_overlap: int = 150,
    md_chunk_size: int = 1000,
    md_chunk_overlap: int = 100,
) -> None:
    """Run the full RareDx pipeline.

    `should_stop`, if provided, is polled between disease searches and between
    articles; when it returns True the run finishes gracefully, saving whatever
    has been collected so far.
    """
    stop = should_stop or (lambda: False)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    raw_bioc_dir = output / "raw_bioc"
    state_dir = output / "state"
    interim_dir = output / "interim"
    pdf_dir = output / "pdfs"
    image_dir = output / "images"

    rag_source = rag_source if rag_source in RAG_SOURCE_OPTIONS else DEFAULT_RAG_SOURCE

    if build_rag and rag_source in {"bioc", "hybrid"} and not save_raw_bioc:
        logger.warning("BioC/Hybrid RAG requires raw BioC JSON; enabling save_raw_bioc.")
        save_raw_bioc = True

    if save_raw_bioc:
        raw_bioc_dir.mkdir(exist_ok=True)
    if download_pdfs:
        pdf_dir.mkdir(exist_ok=True)
    if download_images:
        image_dir.mkdir(exist_ok=True)
    state_dir.mkdir(exist_ok=True)
    interim_dir.mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("RareDx pipeline starting")
    logger.info("Output directory: %s", output.resolve())
    logger.info("Diseases: %s", len(diseases))
    logger.info("Article types: %s", ", ".join(article_types))
    logger.info("Max per disease (per type): %s", max_per_disease)
    logger.info("Download PDFs: %s", download_pdfs)
    logger.info("Download images: %s", download_images)
    logger.info("PMC OA filter: %s", use_pmc_oa_filter)
    logger.info("Build RAG: %s", build_rag)
    logger.info("RAG source: %s", rag_source)
    logger.info("=" * 60)

    # Stage 1
    logger.info("STAGE 1: Searching PubMed per disease")
    pmids, provenance = search_pubmed_by_disease(
        diseases=diseases,
        article_types=article_types,
        email=email,
        api_key=api_key,
        max_per_disease=max_per_disease,
        use_pmc_oa_filter=use_pmc_oa_filter,
        should_stop=stop,
    )
    safe_json_dump(pmids, state_dir / "pmids.json")
    safe_json_dump(provenance, state_dir / "provenance.json")

    if not pmids:
        logger.error("No PMIDs found. Exiting.")
        return

    # Stage 2
    logger.info("STAGE 2: Converting PMIDs to PMCIDs")
    pmid_to_pmcid = map_pmid_to_pmcid(pmids, email=email, api_key=api_key)
    safe_json_dump(pmid_to_pmcid, state_dir / "pmid_to_pmcid.json")

    if not pmid_to_pmcid:
        logger.error("No PMCIDs found. Exiting.")
        return

    all_metadata: list[dict[str, Any]] = []
    all_cases: list[dict[str, Any]] = []
    all_captions: list[dict[str, Any]] = []
    all_images: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    pdf_count = 0
    image_count = 0
    bioc_missing_count = 0
    case_missing_count = 0

    sleep_interval = configure_entrez(email, api_key)

    # Stage 3-6
    logger.info("STAGES 3-6: Processing articles")

    for pmid, pmcid in tqdm(pmid_to_pmcid.items(), desc="Processing articles"):
        if stop():
            logger.warning("Stop requested; halting article processing. "
                           "Saving %s articles collected so far.", len(all_metadata))
            break
        logger.debug("Processing PMID=%s PMCID=%s", pmid, pmcid)

        cases: list[ClinicalCase] = []
        captions: list[dict[str, Any]] = []

        bioc_data = fetch_bioc_article(pmcid, user_agent=user_agent)
        time.sleep(sleep_interval)

        if not bioc_data or not bioc_data.get("documents"):
            logger.warning("No BioC content for %s", pmcid)
            bioc_missing_count += 1
            continue

        if save_raw_bioc:
            safe_json_dump(bioc_data, raw_bioc_dir / f"{pmcid}.json")

        meta = fetch_article_metadata_pubmed(pmid, email=email, api_key=api_key)
        meta.pmcid = pmcid
        time.sleep(sleep_interval)

        # Attach search provenance (which disease query/queries matched this PMID)
        # and the article type. Prefer the actual PubMed publication type if it
        # was classified; otherwise fall back to the search-derived type(s).
        prov = provenance.get(pmid, {})
        meta.diseases = prov.get("diseases", [])
        if not meta.article_type:
            meta.article_type = ";".join(prov.get("article_types", []))

        # License + open-access status (for provenance) from the PMC OA service.
        meta.license, meta.is_open_access = get_pmc_license_and_oa(pmcid, user_agent=user_agent)
        time.sleep(sleep_interval)

        cases = extract_text_from_bioc(
            bioc_data,
            pmcid,
            diseases=meta.diseases,
            article_type=meta.article_type,
        )
        captions = extract_captions_from_bioc(bioc_data, pmcid)

        if not cases:
            case_missing_count += 1
            logger.debug("No text extracted for %s", pmcid)

        pdf_filename = f"{pmcid}.pdf"
        pdf_downloaded = False
        if download_pdfs:
            pdf_path = download_pdf(pmcid, str(pdf_dir), user_agent=user_agent)
            if pdf_path:
                pdf_count += 1
                pdf_downloaded = True
                pdf_filename = os.path.basename(pdf_path)
            time.sleep(sleep_interval)

        # Row for the human-readable TXT summary.
        summary_rows.append(
            {
                "pmcid": pmcid,
                "pdf_filename": pdf_filename if pdf_downloaded else "",
                "title": meta.title or "(title unavailable)",
                "is_open_access": meta.is_open_access,
                "pdf_downloaded": pdf_downloaded,
                "pdf_requested": download_pdfs,
            }
        )

        if download_images:
            images = get_image_urls_from_europepmc(pmcid, user_agent=user_agent)
            time.sleep(EUROPEPMC_RATE_LIMIT)
            for img in images:
                filename = img.get("filename", "image")
                safe_filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
                save_path = str(image_dir / pmcid / safe_filename)
                if download_image(img["url"], save_path, user_agent=user_agent):
                    img["local_path"] = save_path
                    image_count += 1
                all_images.append(img)

        metadata_record = asdict(meta)
        case_records = [asdict(c) for c in cases]

        all_metadata.append(metadata_record)
        all_cases.extend(case_records)
        all_captions.extend(captions)

        # Incremental JSONL audit trail.
        append_jsonl(interim_dir / "metadata.jsonl", [metadata_record])
        append_jsonl(interim_dir / "cases.jsonl", case_records)
        append_jsonl(interim_dir / "captions.jsonl", captions)

    # Save outputs
    logger.info("=" * 60)
    logger.info("Saving final outputs")
    logger.info("=" * 60)

    df_meta = pd.DataFrame(all_metadata)
    df_cases = pd.DataFrame(all_cases)
    df_captions = pd.DataFrame(all_captions)
    df_images = pd.DataFrame(all_images)

    save_dataframe(df_meta, output / "metadata.parquet")
    save_dataframe(df_cases, output / "cases.parquet")
    save_dataframe(df_captions, output / "captions.parquet")
    save_dataframe(df_images, output / "images.parquet")

    # Human-readable per-publication TXT summary.
    write_txt_summary(summary_rows, output / "publication_summary.txt")

    # Stage 8: PDF → Markdown conversion
    md_dir = output / "parsed_markdown"
    markdown_count = 0
    if convert_to_markdown:
        logger.info("STAGE 8: PDF → Markdown conversion")
        markdown_count = convert_pdfs_to_markdown(pdf_dir, md_dir, should_stop=stop)

    # Stage 9: BioC/Markdown → FAISS
    rag_vector_chunks = 0
    if build_rag:
        logger.info("STAGE 9: Building RAG vector database (%s)", rag_source)
        vector_db_dir = output / "vector_db"

        if rag_source == "bioc":
            if raw_bioc_dir.exists() and any(raw_bioc_dir.glob("*.json")):
                rag_vector_chunks = build_rag_database_from_bioc(
                    raw_bioc_dir,
                    vector_db_dir,
                    device=rag_device,
                    bioc_chunk_size=bioc_chunk_size,
                    bioc_chunk_overlap=bioc_chunk_overlap,
                    embedding_model=embedding_model,
                )
            else:
                logger.warning(
                    "Stage 9 skipped: no BioC JSON files found in %s. "
                    "Keep 'Save raw BioC JSON' enabled or choose PDF Markdown RAG.",
                    raw_bioc_dir,
                )

        elif rag_source == "markdown":
            if md_dir.exists() and any(md_dir.glob("*.md")):
                rag_vector_chunks = build_rag_database(
                    md_dir,
                    vector_db_dir,
                    device=rag_device,
                    md_chunk_size=md_chunk_size,
                    md_chunk_overlap=md_chunk_overlap,
                    embedding_model=embedding_model,
                )
            else:
                logger.warning(
                    "Stage 9 skipped: no Markdown files found in %s. "
                    "Enable 'Convert PDFs to Markdown' first or choose BioC JSON RAG.",
                    md_dir,
                )

        elif rag_source == "hybrid":
            has_bioc = raw_bioc_dir.exists() and any(raw_bioc_dir.glob("*.json"))
            has_md = md_dir.exists() and any(md_dir.glob("*.md"))
            if has_bioc or has_md:
                rag_vector_chunks = build_hybrid_rag_database(
                    raw_bioc_dir,
                    md_dir,
                    vector_db_dir,
                    device=rag_device,
                    bioc_chunk_size=bioc_chunk_size,
                    bioc_chunk_overlap=bioc_chunk_overlap,
                    md_chunk_size=md_chunk_size,
                    md_chunk_overlap=md_chunk_overlap,
                    embedding_model=embedding_model,
                )
            else:
                logger.warning(
                    "Stage 9 skipped: no BioC JSON files in %s and no Markdown files in %s.",
                    raw_bioc_dir,
                    md_dir,
                )

    summary = {
        "diseases_searched": len(diseases),
        "article_types": article_types,
        "max_per_disease": max_per_disease,
        "rag_source": rag_source,
        "embedding_model": embedding_model if build_rag else None,
        "bioc_chunk_size": bioc_chunk_size,
        "bioc_chunk_overlap": bioc_chunk_overlap,
        "pmids_retrieved": len(pmids),
        "pmcids_mapped": len(pmid_to_pmcid),
        "articles_processed_with_metadata": len(df_meta),
        "text_records_extracted": len(df_cases),
        "captions_extracted": len(df_captions),
        "pdfs_downloaded": pdf_count,
        "images_downloaded": image_count,
        "articles_missing_bioc": bioc_missing_count,
        "articles_without_extracted_text": case_missing_count,
        "output_directory": str(output.resolve()),
        "markdown_files_created": markdown_count,
        "rag_vector_db_chunks": rag_vector_chunks,
    }
    safe_json_dump(summary, output / "run_summary.json")


    logger.info("PIPELINE COMPLETE")
    for key, value in summary.items():
        logger.info("  %s: %s", key, value)

    if len(df_cases) > 0 and "article_type" in df_cases.columns:
        logger.info("Article-type breakdown:")
        for at, count in df_cases["article_type"].value_counts().items():
            logger.info("  %s: %s", at or "(unknown)", count)

    if len(df_meta) > 0 and "diseases" in df_meta.columns:
        logger.info("Per-disease article counts:")
        disease_counts: dict[str, int] = {}
        for dlist in df_meta["diseases"]:
            for d in (dlist or []):
                disease_counts[d] = disease_counts.get(d, 0) + 1
        for d, count in sorted(disease_counts.items(), key=lambda kv: -kv[1]):
            logger.info("  %s: %s", d, count)


# ---------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RareDx Pipeline: Build a rare-disease review + case-report dataset from PMC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test: 10 articles per disease per type, with PDFs
  python pubvector.py --email you@uni.edu --max-per-disease 10 --download-pdfs --log-level DEBUG

  # Reviews only, all diseases in the built-in panel
  python pubvector.py --email you@uni.edu --article-types review --max-per-disease 200

  # Case reports only for a subset of diseases
  python pubvector.py --email you@uni.edu --article-types case_report \\
      --diseases "Fabry Disease" "Pompe Disease" "Wilson Disease"

  # Full run with images and PDFs
  python pubvector.py --email you@uni.edu --api-key YOUR_KEY \\
      --max-per-disease 1000 --download-images --download-pdfs --output ./raredx_full

  # Test one PMCID PDF download and exit
  python pubvector.py --email you@uni.edu --test-pmcid PMC1234567 --download-pdfs
        """,
    )
    parser.add_argument("--email", required=True, help="Email for NCBI API access")
    parser.add_argument("--api-key", default=None, help="NCBI API key; optional")
    parser.add_argument(
        "--max-per-disease", type=int, default=500,
        help="Maximum articles to retrieve per disease, per article type",
    )
    parser.add_argument(
        "--article-types", nargs="+", default=list(DEFAULT_ARTICLE_TYPES),
        choices=list(ARTICLE_TYPE_CLASSES.keys()),
        help="Which article-type classes to retrieve. Choices: "
             + ", ".join(ARTICLE_TYPE_CLASSES.keys())
             + " (default: review case_report)",
    )
    parser.add_argument(
        "--diseases", nargs="+", default=None,
        help="Subset of disease labels to run (default: full built-in panel). "
             "Labels must match keys in DISEASE_SYNONYMS.",
    )
    parser.add_argument(
        "--list-diseases", action="store_true",
        help="Print the built-in disease panel and exit",
    )
    parser.add_argument(
        "--list-article-types", action="store_true",
        help="Print the available article-type classes and exit",
    )
    parser.add_argument("--output", default="./raredx_data", help="Output directory")
    parser.add_argument("--download-images", action="store_true", help="Download figure images")
    parser.add_argument("--download-pdfs", action="store_true", help="Download article PDFs when available")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--no-pmc-oa-filter", action="store_true", help='Use "pubmed pmc"[sb] (any free PMC full text) instead of the OA subset')
    parser.add_argument("--no-raw-bioc", action="store_true", help="Do not save raw BioC JSON files")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent string")
    parser.add_argument("--test-pmcid", default=None, help="Download PDF for one PMCID and exit")
    parser.add_argument(
        "--convert-to-markdown", action="store_true",
        help="After downloading PDFs, convert each one to Markdown using pymupdf4llm",
    )
    parser.add_argument(
        "--build-rag", action="store_true",
        help="Build a FAISS RAG index in vector_db/.",
    )
    parser.add_argument(
        "--rag-source", default=DEFAULT_RAG_SOURCE, choices=list(RAG_SOURCE_OPTIONS.keys()),
        help="Source used to build the FAISS RAG index: bioc (recommended), markdown, or hybrid.",
    )
    parser.add_argument(
        "--rag-device", default="cpu", choices=["cpu", "cuda"],
        help="Device for the RAG embedding model (default: cpu)",
    )
    parser.add_argument(
        "--bioc-embedding-model", default="bge-small",
        help="Embedding model for the FAISS index: a short name "
             f"({', '.join(BIOC_EMBEDDING_SHORT_NAMES)}) or any HuggingFace "
             "repo ID/URL for a sentence-transformers-compatible model "
             "(default: %(default)s)",
    )
    parser.add_argument(
        "--bioc-chunk-size", type=int, default=1200,
        help="Character chunk size for BioC passage/table splitting when building the RAG DB",
    )
    parser.add_argument(
        "--bioc-chunk-overlap", type=int, default=150,
        help="Character overlap between BioC chunks",
    )
    parser.add_argument(
        "--md-chunk-size", type=int, default=1000,
        help="Character chunk size for Markdown splitting when building the RAG DB",
    )
    parser.add_argument(
        "--md-chunk-overlap", type=int, default=100,
        help="Character overlap between Markdown chunks",
    )
    return parser


def resolve_disease_panel(selected: Optional[list[str]]) -> dict[str, list[str]]:
    """Return the disease->synonyms map, optionally filtered to `selected` labels."""
    if not selected:
        return dict(DISEASE_SYNONYMS)

    panel: dict[str, list[str]] = {}
    unknown: list[str] = []
    # Case-insensitive matching against canonical labels.
    lower_map = {k.lower(): k for k in DISEASE_SYNONYMS}
    for label in selected:
        key = lower_map.get(label.lower())
        if key is None:
            unknown.append(label)
        else:
            panel[key] = DISEASE_SYNONYMS[key]

    if unknown:
        logger.warning(
            "Ignoring unknown disease label(s): %s. Use --list-diseases to see valid labels.",
            ", ".join(unknown),
        )
    return panel


def main(argv: Optional[list[str]] = None) -> int:
    # Allow --list-diseases to work without the otherwise-required --email.
    raw_args = sys.argv[1:] if argv is None else argv
    if "--list-diseases" in raw_args:
        print("Built-in disease panel:\n")
        for label, syns in DISEASE_SYNONYMS.items():
            print(f"  {label}")
            print(f"      synonyms: {', '.join(syns)}")
        return 0

    if "--list-article-types" in raw_args:
        print("Available article-type classes:\n")
        for key, spec in ARTICLE_TYPE_CLASSES.items():
            print(f"  {key}  —  {spec['label']}")
            print(f"      [pt]:  {', '.join(spec['pt'])}")
            print(f"      [tiab]: {', '.join(spec['tiab'])}")
        return 0

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logger.setLevel(args.log_level)
    logging.getLogger().setLevel(args.log_level)

    diseases = resolve_disease_panel(args.diseases)
    if not diseases:
        logger.error("No valid diseases selected. Use --list-diseases to see options.")
        return 1

    print("Starting RareDx pipeline...")
    print(f"Python: {sys.executable}")
    print(f"Output: {Path(args.output).resolve()}")
    print(f"Diseases: {len(diseases)}")
    print(f"Article types: {', '.join(args.article_types)}")
    print(f"Download PDFs: {args.download_pdfs}")
    print(f"Build RAG: {args.build_rag}")
    print(f"RAG source: {args.rag_source}")
    print(f"Log level: {args.log_level}")

    if args.test_pmcid:
        pdf_dir = Path(args.output) / "pdfs"
        pdf_path = download_pdf(args.test_pmcid, str(pdf_dir), user_agent=args.user_agent)
        if pdf_path:
            print(f"PDF downloaded: {pdf_path}")
            return 0
        print(f"No PDF downloaded for {args.test_pmcid}")
        return 1

    run_pipeline(
        email=args.email,
        diseases=diseases,
        article_types=args.article_types,
        api_key=args.api_key,
        max_per_disease=args.max_per_disease,
        output_dir=args.output,
        download_images=args.download_images,
        download_pdfs=args.download_pdfs,
        use_pmc_oa_filter=not args.no_pmc_oa_filter,
        save_raw_bioc=not args.no_raw_bioc,
        user_agent=args.user_agent,
        convert_to_markdown=args.convert_to_markdown,
        build_rag=args.build_rag,
        rag_source=args.rag_source,
        rag_device=args.rag_device,
        embedding_model=resolve_embedding_model(args.bioc_embedding_model),
        bioc_chunk_size=args.bioc_chunk_size,
        bioc_chunk_overlap=args.bioc_chunk_overlap,
        md_chunk_size=args.md_chunk_size,
        md_chunk_overlap=args.md_chunk_overlap,
    )
    return 0




# ---------------------------------------------------------------------
# Chatbot helpers (RAG retrieval + Ollama)
# ---------------------------------------------------------------------

OLLAMA_CHAT_URL   = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL   = "http://localhost:11434/api/tags"
OLLAMA_SHOW_URL   = "http://localhost:11434/api/show"
OLLAMA_CHAT_MODEL = "medgemma:latest"


def read_embedding_model(vector_db_path: str | Path) -> str:
    """Return the embedding model recorded for a vector DB, or the default.

    Indexes built before embedding selection have no embedding_config.json and
    used bge-small, which is the default, so the fallback stays correct.
    """
    cfg = Path(vector_db_path) / EMBEDDING_CONFIG_FILENAME
    if cfg.exists():
        try:
            return json.loads(cfg.read_text()).get(
                "embedding_model", DEFAULT_EMBEDDING_MODEL
            )
        except Exception:
            pass
    return DEFAULT_EMBEDDING_MODEL


def read_chunk_config(vector_db_path: str | Path) -> str:
    """Return a short human-readable summary of the chunk size/overlap and
    RAG source recorded for a vector DB (e.g. 'bioc 1200/150'), or
    'unknown (pre-dates chunk logging)' for indexes built before this was
    recorded in embedding_config.json."""
    cfg = Path(vector_db_path) / EMBEDDING_CONFIG_FILENAME
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text())
            source = data.get("rag_source")
            if source == "bioc":
                return f"bioc {data['bioc_chunk_size']}/{data['bioc_chunk_overlap']}"
            if source == "markdown":
                return f"md {data['md_chunk_size']}/{data['md_chunk_overlap']}"
            if source == "hybrid":
                return (
                    f"bioc {data['bioc_chunk_size']}/{data['bioc_chunk_overlap']} "
                    f"+ md {data['md_chunk_size']}/{data['md_chunk_overlap']}"
                )
        except Exception:
            pass
    return "unknown (pre-dates chunk logging)"


def load_chat_vector_db(vector_db_path: str, device: str = "cpu"):
    """Load a FAISS vector database for the chatbot.

    Loads the same embedding model that built the index (recorded in
    embedding_config.json); returns the vectorstore, or None on failure.
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
    except ImportError:
        logger.error(
            "Missing RAG deps. Run: pip install langchain-community "
            "langchain-huggingface faiss-cpu sentence-transformers"
        )
        return None

    path = Path(vector_db_path)
    if not (path / "index.faiss").exists():
        return None

    embedding_model = read_embedding_model(path)
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )
        return FAISS.load_local(
            str(path), embeddings, allow_dangerous_deserialization=True
        )
    except Exception as exc:
        logger.error("Failed to load vector DB (%s): %s", embedding_model, exc)
        return None


def _format_chat_context(docs) -> str:
    parts = []
    for i, doc in enumerate(docs):
        md = doc.metadata or {}
        source = md.get("source", "Unknown")
        section = md.get("section", "N/A")
        rag_source = md.get("rag_source", "unknown")
        chunk_kind = md.get("chunk_kind", "text")
        pmcid = md.get("pmcid", "")
        passage_index = md.get("passage_index", "")
        chunk_id = md.get("chunk_id", "")
        cite_label = f"{source}"
        if pmcid:
            cite_label += f" | PMCID: {pmcid}"
        if passage_index != "":
            cite_label += f" | passage {passage_index}"
        if chunk_id != "":
            cite_label += f" | chunk {chunk_id}"

        parts.append(
            f"--- DOCUMENT {i + 1} ({cite_label}; Section: {section}; "
            f"Kind: {chunk_kind}; RAG source: {rag_source}) ---\n"
            f"{doc.page_content}"
        )
    return "\n\n".join(parts)


def _build_rag_prompt(query: str, context: str, history: list) -> str:
    history_block = ""
    if history:
        lines = [
            ("User" if m["role"] == "user" else "Assistant") + f": {m['content']}"
            for m in history[-6:]  # last 3 turns to keep context manageable
        ]
        history_block = (
            "\n<conversation_history>\n"
            + "\n".join(lines)
            + "\n</conversation_history>\n"
        )

    return (
        "<system>\n"
        "You are an expert medical AI assistant specialising in rare diseases "
        "and lysosomal storage disorders.\n\n"
        "Answer the user\'s clinical question using ONLY the provided context documents. "
        "Rules:\n"
        "- Focus exclusively on clinical, biochemical, genetic, and therapeutic content.\n"
        "- Structure your response with clear headings relevant to the question "
        "(e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment).\n"
        "- Only include sections directly supported by the retrieved context.\n"
        "- Cite supporting evidence inline using the document source/PMCID/section information shown in the context headers.\n"
        "- Be concise and precise. Avoid padding.\n"
        "- If the context is insufficient, say so clearly rather than speculating.\n"
        "- Use the conversation history to maintain continuity when relevant.\n"
        "</system>\n\n"
        f"<context>\n{context}\n</context>\n"
        f"{history_block}"
        f"<user_query>\n{query}\n</user_query>\n\n"
        "Final Evidence-Based Answer:"
    )


def list_ollama_models() -> list[str]:
    """Return installed Ollama model tags, or [] if Ollama is unreachable."""
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def model_supports_thinking(model: str) -> bool:
    """True if the Ollama model advertises the 'thinking' capability."""
    try:
        resp = requests.post(OLLAMA_SHOW_URL, json={"model": model}, timeout=5)
        resp.raise_for_status()
        return "thinking" in (resp.json().get("capabilities") or [])
    except Exception:
        return False


def _stream_ollama(prompt: str, model: str = OLLAMA_CHAT_MODEL, think: bool = False):
    """Yield (kind, text) pairs from Ollama; kind is "thinking" or "response".

    When think is False, "thinking" models (e.g. qwen3) otherwise spend the whole
    token budget reasoning and return an empty answer. Ollama ignores the flag for
    models that don't support thinking.
    """
    payload = {
        "model":   model,
        "prompt":  prompt,
        "stream":  True,
        "think":   think,
        # Thinking spends tokens on a reasoning pass before the answer, so give it
        # a larger budget or the answer can be cut off entirely.
        "options": {
            "num_predict": 4096 if think else 1024,
            "temperature": 0.2,
        },
    }
    try:
        with requests.post(
            OLLAMA_CHAT_URL, json=payload, stream=True, timeout=120
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if chunk.get("error"):
                    yield ("response", f"Ollama error: {chunk['error']}")
                    break
                if chunk.get("thinking"):
                    yield ("thinking", chunk["thinking"])
                piece = chunk.get("response", "")
                if piece:
                    yield ("response", piece)
                if chunk.get("done"):
                    break
    except Exception as exc:
        yield ("response", f"Ollama error: {exc}")


# Persisted UI settings so students don't retype email/output/model each launch.
# API keys are intentionally never written to disk.
USER_CONFIG_PATH = Path.home() / ".config" / "pubvector" / "config.json"


def load_user_config() -> dict:
    """Load persisted UI settings (email, output dir, last model)."""
    try:
        return json.loads(USER_CONFIG_PATH.read_text())
    except Exception:
        return {}


def save_user_config(updates: dict) -> None:
    """Merge updates into the persisted UI settings on disk."""
    cfg = load_user_config()
    cfg.update(updates)
    try:
        USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        USER_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as exc:
        logger.warning("Could not save user config: %s", exc)


# ---------------------------------------------------------------------
# Streamlit web app
# ---------------------------------------------------------------------

def run_app() -> None:
    """Render the PubVector Streamlit interface."""
    import streamlit as st

    # ---------------------------------------------------------------------
    # Page config & styling
    # ---------------------------------------------------------------------

    st.set_page_config(
        page_title="PubVector",
        page_icon="📖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

          :root {
            --pd-ink: #f3ede6;          /* light warm text */
            --pd-muted: #9c9087;         /* muted warm gray */
            --pd-paper: #16130f;         /* deep warm charcoal */
            --pd-card: #211c17;          /* raised surface */
            --pd-accent: #e8896b;        /* glowing terracotta */
            --pd-accent-2: #d4633f;      /* rust */
            --pd-accent-soft: #4a3328;   /* dim ember (loader track) */
            --pd-line: #3a322b;          /* warm border */
          }

          html, body, [class*="css"] {
            font-family: 'IBM Plex Sans', sans-serif;
            color: var(--pd-ink);
          }

          /* Dark warm surfaces */
          [data-testid="stAppViewContainer"] {
            background:
              radial-gradient(1100px 480px at 12% -8%, #2a1d16 0%, rgba(42,29,22,0) 60%),
              radial-gradient(900px 420px at 100% 0%, #241a1f 0%, rgba(36,26,31,0) 55%),
              var(--pd-paper);
            color: var(--pd-ink);
          }
          [data-testid="stSidebar"] {
            background: #1b1611;
            border-right: 1px solid var(--pd-line);
          }

          /* Keep Streamlit's own text + widgets readable on dark */
          [data-testid="stAppViewContainer"] *,
          [data-testid="stSidebar"] * {
            color: var(--pd-ink);
          }
          .stTextInput input, .stTextArea textarea, .stNumberInput input,
          [data-baseweb="select"] > div, [data-baseweb="input"] > div {
            background-color: var(--pd-card) !important;
            color: var(--pd-ink) !important;
            border-color: var(--pd-line) !important;
          }
          .stTextInput input::placeholder, .stTextArea textarea::placeholder {
            color: var(--pd-muted) !important;
          }

          /* Header logo + wordmark */
          .pd-header {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            margin-bottom: 0.15rem;
          }
          .pd-logo {
            flex: 0 0 auto;
            filter: drop-shadow(0 4px 10px rgba(232,137,107,0.22));
          }
          .pd-wordmark {
            font-family: 'Fraunces', serif;
            font-size: 2.6rem;
            font-weight: 600;
            letter-spacing: -0.5px;
            line-height: 1;
            background: linear-gradient(95deg, var(--pd-accent) 0%, var(--pd-accent-2) 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
          }
          .pd-sub {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.78rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--pd-muted);
            margin: 0.1rem 0 1.3rem 0;
          }
          .pd-rule {
            height: 2px;
            background: linear-gradient(90deg, var(--pd-accent) 0%, var(--pd-accent-2) 38%, transparent 100%);
            border: none;
            border-radius: 2px;
            margin: 0.2rem 0 1.5rem 0;
          }
          .pd-card {
            background: var(--pd-card);
            border: 1px solid var(--pd-line);
            border-radius: 14px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 6px 24px rgba(0,0,0,0.35);
          }

          /* Buttons: rounded, light, gradient primary */
          div.stButton > button {
            font-family: 'IBM Plex Mono', monospace;
            font-weight: 500;
            letter-spacing: 0.03em;
            border-radius: 10px;
            border: 1px solid var(--pd-line);
            transition: transform 0.08s ease, box-shadow 0.15s ease;
          }
          div.stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(232,137,107,0.18);
          }
          div.stButton > button[kind="primary"] {
            background: linear-gradient(95deg, var(--pd-accent) 0%, var(--pd-accent-2) 100%);
            border: none;
            color: #fff;
          }

          code, pre, .stCode {
            font-family: 'IBM Plex Mono', monospace !important;
          }
          /* Dark log / code blocks */
          [data-testid="stCode"], pre {
            background: #0e0b08 !important;
            border: 1px solid var(--pd-line) !important;
            border-radius: 10px !important;
          }
          [data-testid="stCode"] code, pre code {
            color: #e9ddd2 !important;
            background: transparent !important;
          }
          .pd-metric-label {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: var(--pd-muted);
          }

          /* ---- Animated loading icon ---- */
          .pd-loader-wrap {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            padding: 0.6rem 0.95rem;
            background: var(--pd-card);
            border: 1px solid var(--pd-line);
            border-radius: 12px;
            box-shadow: 0 6px 22px rgba(232,137,107,0.10);
            width: fit-content;
          }
          .pd-loader {
            position: relative;
            width: 30px; height: 30px;
            flex: 0 0 auto;
          }
          .pd-loader .ring {
            position: absolute; inset: 0;
            border: 3px solid var(--pd-accent-soft);
            border-top-color: var(--pd-accent);
            border-right-color: var(--pd-accent-2);
            border-radius: 50%;
            animation: pd-spin 0.9s cubic-bezier(0.5,0.1,0.4,0.9) infinite;
          }
          .pd-loader .dot {
            position: absolute;
            top: 50%; left: 50%;
            width: 7px; height: 7px;
            margin: -3.5px 0 0 -3.5px;
            background: var(--pd-accent-2);
            border-radius: 50%;
            animation: pd-pulse 0.9s ease-in-out infinite;
          }
          @keyframes pd-spin { to { transform: rotate(360deg); } }
          @keyframes pd-pulse {
            0%, 100% { transform: scale(0.7); opacity: 0.5; }
            50%      { transform: scale(1.15); opacity: 1; }
          }
          .pd-loader-text {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.85rem;
            color: var(--pd-ink);
          }
          .pd-loader-text b { color: var(--pd-accent); }
          .pd-loader-dots::after {
            content: '';
            animation: pd-ellipsis 1.4s steps(4, end) infinite;
          }
          @keyframes pd-ellipsis {
            0%   { content: ''; }
            25%  { content: '.'; }
            50%  { content: '..'; }
            75%  { content: '...'; }
          }

          /* ---- Tabs ---- */
          [data-baseweb="tab-list"] {
            gap: 0.35rem;
            border-bottom: 1px solid var(--pd-line);
          }
          button[data-baseweb="tab"] {
            font-family: 'IBM Plex Mono', monospace;
            letter-spacing: 0.04em;
            border-radius: 10px 10px 0 0;
          }
          button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--pd-accent) !important;
          }
          [data-baseweb="tab-highlight"] {
            background: linear-gradient(90deg, var(--pd-accent), var(--pd-accent-2)) !important;
            height: 3px;
          }

          /* ---- Expanders: match the card surface ---- */
          [data-testid="stExpander"] {
            border: 1px solid var(--pd-line);
            border-radius: 12px;
            background: var(--pd-card);
            overflow: hidden;
          }
          [data-testid="stExpander"] summary {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.82rem;
            letter-spacing: 0.02em;
          }

          /* ---- Chat bubbles + input ---- */
          [data-testid="stChatMessage"] {
            background: var(--pd-card);
            border: 1px solid var(--pd-line);
            border-radius: 14px;
            padding: 0.3rem 0.95rem;
          }
          [data-testid="stChatInput"] textarea {
            background: var(--pd-card) !important;
            color: var(--pd-ink) !important;
          }

          /* ---- Alerts: warm rounded ---- */
          [data-testid="stAlert"] { border-radius: 12px; }

          /* ---- Onboarding step strip ---- */
          .pd-steps {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin: 0 0 1.4rem 0;
          }
          .pd-step {
            flex: 1 1 150px;
            background: var(--pd-card);
            border: 1px solid var(--pd-line);
            border-radius: 12px;
            padding: 0.7rem 0.9rem;
          }
          .pd-step .n {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.68rem; letter-spacing: 0.12em;
            color: var(--pd-accent);
            text-transform: uppercase;
          }
          .pd-step .t { font-weight: 600; font-size: 0.92rem; margin-top: 0.18rem; }
          .pd-step .d {
            color: var(--pd-muted); font-size: 0.79rem;
            margin-top: 0.12rem; line-height: 1.35;
          }

          /* ---- Metric cards (pre-run summary) ---- */
          .pd-metric {
            background: var(--pd-card);
            border: 1px solid var(--pd-line);
            border-radius: 12px;
            padding: 0.7rem 0.95rem;
            text-align: center;
          }
          .pd-metric .v {
            font-family: 'Fraunces', serif;
            font-size: 1.95rem; font-weight: 600; line-height: 1;
            color: var(--pd-ink);
          }

          /* ---- Empty-state card ---- */
          .pd-empty {
            background: var(--pd-card);
            border: 1px dashed var(--pd-line);
            border-radius: 14px;
            padding: 1.4rem 1.5rem;
            text-align: center;
            color: var(--pd-muted);
          }
          .pd-empty h3 {
            font-family: 'Fraunces', serif;
            color: var(--pd-ink);
            margin: 0 0 0.35rem 0;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


    # PubVector logo (inline SVG): an open book whose pages rise into a
    # "digest" pulse line — knowledge condensed into a signal.
    PD_LOGO_SVG = """
    <svg class="pd-logo" width="46" height="46" viewBox="0 0 46 46" fill="none"
         xmlns="http://www.w3.org/2000/svg" role="img" aria-label="PubVector logo">
      <defs>
        <linearGradient id="pdg" x1="0" y1="0" x2="46" y2="46" gradientUnits="userSpaceOnUse">
          <stop stop-color="#e8896b"/>
          <stop offset="1" stop-color="#d4633f"/>
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="42" height="42" rx="12" fill="#2a1d16"/>
      <rect x="2.5" y="2.5" width="41" height="41" rx="11.5" stroke="url(#pdg)" stroke-opacity="0.6"/>
      <!-- book spine + pages -->
      <path d="M23 14.5C20.4 12.7 16.8 12.3 13.5 13.2V31.4C16.8 30.5 20.4 30.9 23 32.7
               C25.6 30.9 29.2 30.5 32.5 31.4V13.2C29.2 12.3 25.6 12.7 23 14.5Z"
            fill="#16130f" stroke="url(#pdg)" stroke-width="1.8" stroke-linejoin="round"/>
      <path d="M23 14.5V32.7" stroke="url(#pdg)" stroke-width="1.8" stroke-linecap="round"/>
      <!-- digest pulse line across the pages -->
      <path d="M15.5 25H18L19.4 22L21 28L22.2 25" stroke="url(#pdg)"
            stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <path d="M23.8 25L25 22L26.6 28L28 25H30.5" stroke="url(#pdg)"
            stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </svg>
    """


    # ---------------------------------------------------------------------
    # Log streaming infrastructure
    # ---------------------------------------------------------------------

    class QueueLogHandler(logging.Handler):
        """A logging handler that pushes formatted records onto a queue."""

        def __init__(self, log_queue: "queue.Queue[str]") -> None:
            super().__init__()
            self.log_queue = log_queue

        def emit(self, record: logging.LogRecord) -> None:
            try:
                self.log_queue.put(self.format(record))
            except Exception:
                pass


    def run_pipeline_worker(params: dict[str, Any], log_queue: "queue.Queue[str]",
                            result: dict[str, Any], stop_event: threading.Event) -> None:
        """Run the pipeline in a worker thread, capturing logs and outcome."""
        handler = QueueLogHandler(log_queue)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
        pipeline_logger = logging.getLogger("raredx")
        pipeline_logger.addHandler(handler)
        pipeline_logger.setLevel(params.get("log_level", "INFO"))

        try:
            run_pipeline(
                email=params["email"],
                diseases=params["diseases"],
                article_types=params["article_types"],
                api_key=params["api_key"] or None,
                max_per_disease=params["max_per_disease"],
                output_dir=params["output_dir"],
                download_images=params["download_images"],
                download_pdfs=params["download_pdfs"],
                use_pmc_oa_filter=params["use_pmc_oa_filter"],
                save_raw_bioc=params["save_raw_bioc"],
                user_agent=params["user_agent"],
                should_stop=stop_event.is_set,
                convert_to_markdown=params["convert_to_markdown"],
                build_rag=params["build_rag"],
                rag_source=params["rag_source"],
                rag_device=params["rag_device"],
                embedding_model=params["embedding_model"],
                bioc_chunk_size=params["bioc_chunk_size"],
                bioc_chunk_overlap=params["bioc_chunk_overlap"],
                md_chunk_size=params["md_chunk_size"],
                md_chunk_overlap=params["md_chunk_overlap"],
            )
            result["status"] = "stopped" if stop_event.is_set() else "done"
        except Exception as e:  # noqa: BLE001 - surface any failure to the UI
            result["status"] = "error"
            result["error"] = str(e)
            pipeline_logger.error("Pipeline failed: %s", e)
        finally:
            pipeline_logger.removeHandler(handler)
            log_queue.put("__PIPELINE_COMPLETE__")


    # ---------------------------------------------------------------------
    # Session state
    # ---------------------------------------------------------------------

    def init_state() -> None:
        defaults = {
            "running": False,
            "log_lines": [],
            "log_queue": None,
            "worker": None,
            "result": {},
            "output_dir": "",
            "stop_event": None,
            "stop_requested": False,
            "chat_messages": [],
            "create_chatbot": False,
            "rag_search_root": "./raredx_data",
            "selected_pubvector_output_dir": "",
            "selected_vector_db_path": "",
            "active_backend": None,
            "active_backend_key": "",
            "active_pubvector_output_dir": "",
        }
        for k, v in defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v


    init_state()

    if "user_config" not in st.session_state:
        st.session_state.user_config = load_user_config()
    cfg = st.session_state.user_config


    # ---------------------------------------------------------------------
    # Header
    # ---------------------------------------------------------------------

    st.markdown(
        f'<div class="pd-header">{PD_LOGO_SVG}'
        f'<span class="pd-wordmark">PubVector</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pd-sub">PubMed / PMC &nbsp;·&nbsp; reviews + case reports &nbsp;·&nbsp; RAG-ready</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="pd-rule">', unsafe_allow_html=True)


    # ---------------------------------------------------------------------
    # Sidebar: credentials + run controls
    # ---------------------------------------------------------------------

    with st.sidebar:
        st.markdown("### NCBI Access")
        email = st.text_input(
            "Email *",
            value=cfg.get("email", ""),
            placeholder="you@institution.edu",
            help="Required by NCBI Entrez for all API access.",
        )
        api_key = st.text_input(
            "API key (optional)",
            value="",
            type="password",
            help="An NCBI API key raises the rate limit from ~3 to ~10 requests/sec. "
                 "Strongly recommended for large runs.",
        )

        st.markdown("---")
        st.markdown("### Output")
        output_dir = st.text_input(
            "Output directory",
            value=cfg.get("output_dir", "./raredx_data"),
            help="Where all parquet/jsonl/txt outputs are written.",
        )
        user_agent = st.text_input("HTTP User-Agent", value=DEFAULT_USER_AGENT)

        st.markdown("---")
        st.caption(
            "Tip: large multi-disease runs make many API calls. "
            "Use an API key and a modest *max per disease* first."
        )


    # ------------------------------------------------------------------
    # Tabs: Pipeline  |  Chatbot
    # ------------------------------------------------------------------

    tab1, tab2 = st.tabs(["⚙  Pipeline", "💬  Chatbot"])

    with tab1:

        # First-run guidance — hidden once a run has produced output this session.
        if not st.session_state.running and not st.session_state.output_dir:
            st.markdown(
                '<div class="pd-steps">'
                '<div class="pd-step"><div class="n">Step 1</div>'
                '<div class="t">Add your email</div>'
                '<div class="d">NCBI requires it (left sidebar). An API key is optional '
                'but speeds up large runs.</div></div>'
                '<div class="pd-step"><div class="n">Step 2</div>'
                '<div class="t">Pick diseases &amp; types</div>'
                '<div class="d">One search group per line, then choose article types '
                'like reviews and case reports.</div></div>'
                '<div class="pd-step"><div class="n">Step 3</div>'
                '<div class="t">Build knowledge base</div>'
                '<div class="d">Turn on Build RAG vector database, then click Build. '
                'Outputs land in your folder.</div></div>'
                '<div class="pd-step"><div class="n">Step 4</div>'
                '<div class="t">Chat with it</div>'
                '<div class="d">Open the Chatbot tab and ask questions — answers cite '
                'their PubMed sources.</div></div>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ---------------------------------------------------------------------
        # Main: parameters
        # ---------------------------------------------------------------------

        left, right = st.columns([1.15, 1], gap="large")

        with left:
            st.markdown("#### 1 · Keywords")

            custom_raw = st.text_area(
                "Search terms",
                value="",
                height=240,
                placeholder=(
                    "One search group per line, e.g.\n"
                    "Fabry disease\n"
                    "Pompe disease\n"
                    "Wilson disease, Wilson's disease, hepatolenticular degeneration"
                ),
                help="Each line is one search group, matched in title/abstract. "
                     "Put synonyms on the same line separated by commas to OR them "
                     "together into a single group (e.g. an abbreviation and its full name).",
            )
            st.caption(
                "Tip: comma-separate synonyms on a line to broaden recall, "
                "e.g. `MPS II, mucopolysaccharidosis type II, Hunter syndrome`."
            )

        with right:
            st.markdown("#### 2 · Article types & search")

            article_types_labels = st.multiselect(
                "Article types",
                options=[spec["label"] for spec in ARTICLE_TYPE_CLASSES.values()],
                default=[
                    ARTICLE_TYPE_CLASSES[k]["label"] for k in DEFAULT_ARTICLE_TYPES
                ],
                help="Each class OR-s its exact PubMed [pt] tokens with free-text "
                     "[tiab] fallbacks. Case reports & series capture the case "
                     "narrative; other classes capture full body text.",
            )

            max_per_disease = st.number_input(
                "Max articles per disease (per type)",
                min_value=1, max_value=10000, value=100, step=1,
                help="Upper bound on PMIDs fetched for each disease and each article type.",
            )

            use_pmc_oa_filter = st.toggle(
                "Restrict to PMC Open Access Subset",
                value=True,
                help="ON: only OA-subset articles (redistributable license, license field populated). "
                     "OFF: any free full text in PMC (broader recall, license may be empty).",
            )

            st.markdown("#### 3 · Downloads & chunking")
            c1, c2 = st.columns(2)
            with c1:
                download_pdfs = st.toggle("Download PDFs", value=True)
                save_raw_bioc = st.toggle("Save raw BioC JSON", value=True)
            with c2:
                download_images = st.toggle("Download figure images", value=False)

            st.markdown("#### 4 · RAG database")

            st.caption(
                "BioC JSON is the recommended RAG source because it preserves "
                "article structure, section labels, tables, captions, and identifiers. "
                "PDF Markdown remains available as a fallback or hybrid enrichment layer."
            )

            build_rag = st.toggle(
                "Build RAG vector database",
                value=False,
                help="Embed article chunks into a FAISS index (bge-small or bge-base). "
                     "Output goes to vector_db/ and can be loaded by the Chatbot tab.",
            )

            if build_rag:
                rag_source_label = st.selectbox(
                    "RAG source",
                    options=list(RAG_SOURCE_OPTIONS.values()),
                    index=list(RAG_SOURCE_OPTIONS.keys()).index(DEFAULT_RAG_SOURCE),
                    help="BioC JSON is cleaner and more structured. PDF Markdown can be used when BioC is unavailable or for hybrid enrichment.",
                )
                rag_source = {v: k for k, v in RAG_SOURCE_OPTIONS.items()}[rag_source_label]
            else:
                rag_source = DEFAULT_RAG_SOURCE

            needs_markdown = build_rag and rag_source in {"markdown", "hybrid"}
            needs_bioc = build_rag and rag_source in {"bioc", "hybrid"}

            if needs_bioc and not save_raw_bioc:
                st.warning("BioC/Hybrid RAG needs raw BioC JSON; it will be saved for this run.")
                save_raw_bioc = True

            cr1, cr2 = st.columns(2)
            with cr1:
                convert_to_markdown = st.toggle(
                    "Convert PDFs to Markdown",
                    value=needs_markdown,
                    disabled=not needs_markdown,
                    help="Required for PDF Markdown or Hybrid RAG. BioC-only RAG does not need PDF conversion.",
                )
            with cr2:
                if needs_markdown and not download_pdfs:
                    st.warning("PDF Markdown/Hybrid RAG requires PDFs. Enable PDF download or use an existing parsed_markdown/ folder.")

            cr6, _ = st.columns(2)
            with cr6:
                create_chatbot = st.toggle(
                    "Create Chatbot",
                    value=st.session_state.create_chatbot,
                    disabled=not build_rag,
                    help="Launch a RAG-powered chatbot in the Chatbot tab once the vector "
                         "database is ready. Only available when 'Build RAG vector database' "
                         "is enabled.",
                )
            st.session_state.create_chatbot = create_chatbot

            if build_rag:
                cr3, cr4, cr5 = st.columns(3)
                with cr3:
                    rag_device = st.selectbox(
                        "Embedding device",
                        ["cpu", "cuda"],
                        index=0,
                        help="Device for the embedding model.",
                    )
                with cr4:
                    bioc_chunk_size = st.number_input(
                        "BioC chunk size (chars)",
                        min_value=100, max_value=4000, value=1200, step=100,
                        disabled=not needs_bioc,
                        help="Character chunk size for BioC passages and tables.",
                    )
                with cr5:
                    bioc_chunk_overlap = st.number_input(
                        "BioC chunk overlap (chars)",
                        min_value=0, max_value=500, value=150, step=10,
                        disabled=not needs_bioc,
                        help="Character overlap between BioC chunks.",
                    )

                with st.expander("Advanced · embedding model"):
                    cached_models = list_cached_embedding_models()
                    if "custom_embedding_models" not in st.session_state:
                        st.session_state.custom_embedding_models = []

                    _emb_keys = list(EMBEDDING_MODELS.keys())
                    for _m in cached_models + st.session_state.custom_embedding_models:
                        if _m not in _emb_keys:
                            _emb_keys.append(_m)

                    def _emb_label(model_id: str) -> str:
                        icon = "✅" if model_id in cached_models else "⬇️"
                        return f"{icon} {EMBEDDING_MODELS.get(model_id, model_id)}"

                    _emb_labels = [_emb_label(m) for m in _emb_keys]
                    _default_idx = (
                        _emb_keys.index(DEFAULT_EMBEDDING_MODEL)
                        if DEFAULT_EMBEDDING_MODEL in _emb_keys else 0
                    )
                    _emb_choice = st.selectbox(
                        "Embedding model",
                        options=_emb_labels,
                        index=_default_idx,
                        help="Any sentence-transformers-compatible HuggingFace model can "
                             "embed the chunks into the FAISS index. ✅ = already downloaded "
                             "and cached locally. ⬇️ = will be downloaded from HuggingFace "
                             "the first time you build with it selected (size varies by "
                             "model). The choice is saved with the index, so the chatbot "
                             "loads a matching model automatically.",
                    )
                    embedding_model = _emb_keys[_emb_labels.index(_emb_choice)]
                    st.caption(
                        "An index is tied to one embedding model — rebuild the database to switch."
                    )

                    st.markdown("**Add a custom HuggingFace embedding model**")
                    _cc1, _cc2 = st.columns([3, 1])
                    with _cc1:
                        _custom_model_input = st.text_input(
                            "HuggingFace model ID or URL",
                            placeholder="e.g. pritamdeka/S-PubMedBert-MS-MARCO",
                            label_visibility="collapsed",
                        )
                    with _cc2:
                        if st.button("➕ Add", use_container_width=True):
                            _repo_id = normalize_hf_model_id(_custom_model_input)
                            if _repo_id:
                                if _repo_id not in st.session_state.custom_embedding_models:
                                    st.session_state.custom_embedding_models.append(_repo_id)
                                st.rerun()
                            else:
                                st.warning(
                                    "Couldn't parse that as a HuggingFace model — use the "
                                    "`org/model-name` format or paste the model's "
                                    "HuggingFace URL."
                                )

                if needs_markdown:
                    cr7, cr8 = st.columns(2)
                    with cr7:
                        md_chunk_size = st.number_input(
                            "MD chunk size (chars)",
                            min_value=100, max_value=4000, value=1000, step=100,
                            help="Character chunk size for Markdown splitting.",
                        )
                    with cr8:
                        md_chunk_overlap = st.number_input(
                            "MD chunk overlap (chars)",
                            min_value=0, max_value=500, value=100, step=10,
                            help="Character overlap between Markdown chunks.",
                        )
                else:
                    md_chunk_size = 1000
                    md_chunk_overlap = 100
            else:
                rag_device = "cpu"
                embedding_model = DEFAULT_EMBEDDING_MODEL
                bioc_chunk_size = 1200
                bioc_chunk_overlap = 150
                md_chunk_size = 1000
                md_chunk_overlap = 100
                convert_to_markdown = False

            log_level = st.selectbox("Log level", ["INFO", "DEBUG", "WARNING", "ERROR"], index=0)


        # ---------------------------------------------------------------------
        # Assemble the disease/keyword map
        # ---------------------------------------------------------------------

        def build_disease_map(keyword_text: str) -> dict[str, list[str]]:
            """Parse user keyword lines into a label->terms map.

            Each non-empty line is one search group. Terms separated by commas on a
            line are OR-ed together within that group; the group's label is the first
            term. Duplicate labels are de-duplicated (first occurrence wins).
            """
            disease_map: dict[str, list[str]] = {}
            for line in keyword_text.splitlines():
                terms = [t.strip() for t in line.split(",") if t.strip()]
                if not terms:
                    continue
                label = terms[0]
                # Don't clobber an earlier group that used the same label.
                disease_map.setdefault(label, terms)
            return disease_map


        def map_article_types(labels: list[str]) -> list[str]:
            """Map selected display labels to internal class keys, preserving
            registry order so downstream tags are deterministic."""
            selected = {ARTICLE_TYPE_LABEL_TO_KEY[l] for l in labels
                        if l in ARTICLE_TYPE_LABEL_TO_KEY}
            return [k for k in ARTICLE_TYPE_CLASSES if k in selected]


        disease_map = build_disease_map(custom_raw)
        article_types = map_article_types(article_types_labels)

        st.markdown('<hr class="pd-rule">', unsafe_allow_html=True)

        # Pre-run summary
        sc1, sc2, sc3 = st.columns(3)
        sc1.markdown(
            '<div class="pd-metric"><div class="pd-metric-label">Search groups</div>'
            f'<div class="v">{len(disease_map)}</div></div>',
            unsafe_allow_html=True,
        )
        sc2.markdown(
            '<div class="pd-metric"><div class="pd-metric-label">Article types</div>'
            f'<div class="v">{len(article_types)}</div></div>',
            unsafe_allow_html=True,
        )
        sc3.markdown(
            '<div class="pd-metric"><div class="pd-metric-label">Max queries</div>'
            f'<div class="v">{len(disease_map) * max(len(article_types), 1)}</div></div>',
            unsafe_allow_html=True,
        )


        # ---------------------------------------------------------------------
        # Validation + Run button
        # ---------------------------------------------------------------------

        def validate() -> list[str]:
            errors = []
            if not email.strip():
                errors.append("Email is required for NCBI access.")
            if "@" not in email:
                errors.append("Email looks invalid.")
            if not disease_map:
                errors.append("Enter at least one search term.")
            if not article_types:
                errors.append("Select at least one article type.")
            return errors


        run_col, _ = st.columns([1, 3])
        with run_col:
            start_clicked = st.button(
                "▶  Build knowledge base",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.running,
            )

        if start_clicked and not st.session_state.running:
            errors = validate()
            if errors:
                for e in errors:
                    st.error(e)
            else:
                # Kick off the worker thread.
                log_q: "queue.Queue[str]" = queue.Queue()
                result: dict[str, Any] = {"status": "running"}
                stop_event = threading.Event()
                params = {
                    "email": email.strip(),
                    "api_key": api_key.strip(),
                    "diseases": disease_map,
                    "article_types": article_types,
                    "max_per_disease": int(max_per_disease),
                    "output_dir": output_dir.strip() or "./raredx_data",
                    "download_images": download_images,
                    "download_pdfs": download_pdfs,
                    "use_pmc_oa_filter": use_pmc_oa_filter,
                    "save_raw_bioc": save_raw_bioc,
                    "user_agent": user_agent.strip() or DEFAULT_USER_AGENT,
                    "log_level": log_level,
                    "convert_to_markdown": convert_to_markdown,
                    "build_rag": build_rag,
                    "rag_source": rag_source,
                    "rag_device": rag_device,
                    "embedding_model": embedding_model,
                    "bioc_chunk_size": int(bioc_chunk_size),
                    "bioc_chunk_overlap": int(bioc_chunk_overlap),
                    "md_chunk_size": int(md_chunk_size),
                    "md_chunk_overlap": int(md_chunk_overlap),
                }
                save_user_config(
                    {"email": params["email"], "output_dir": params["output_dir"]}
                )
                cfg.update(
                    {"email": params["email"], "output_dir": params["output_dir"]}
                )
                worker = threading.Thread(
                    target=run_pipeline_worker, args=(params, log_q, result, stop_event), daemon=True
                )
                worker.start()

                st.session_state.running = True
                st.session_state.log_lines = []
                st.session_state.log_queue = log_q
                st.session_state.worker = worker
                st.session_state.result = result
                st.session_state.output_dir = params["output_dir"]
                st.session_state.stop_event = stop_event
                st.session_state.stop_requested = False
                st.rerun()


        # ---------------------------------------------------------------------
        # Live log streaming while running
        # ---------------------------------------------------------------------

        if st.session_state.running:
            # Stop control.
            stop_col, status_col = st.columns([1, 3])
            with stop_col:
                stop_clicked = st.button(
                    "■  Stop run",
                    type="secondary",
                    use_container_width=True,
                    disabled=st.session_state.stop_requested,
                )
            if stop_clicked and st.session_state.stop_event is not None:
                st.session_state.stop_event.set()
                st.session_state.stop_requested = True

            with status_col:
                if st.session_state.stop_requested:
                    st.warning("Stop requested — finishing the current item, then saving and exiting.")

            # Animated loading indicator.
            loader_state = "Stopping" if st.session_state.stop_requested else "Working"
            st.markdown(
                f"""
                <div class="pd-loader-wrap">
                  <div class="pd-loader"><div class="ring"></div><div class="dot"></div></div>
                  <div class="pd-loader-text"><b>{loader_state}</b><span class="pd-loader-dots"></span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("#### Live log")
            log_box = st.empty()
            progress_note = st.empty()

            log_q = st.session_state.log_queue
            complete = False

            # Drain whatever is currently in the queue, then refresh.
            while True:
                try:
                    line = log_q.get_nowait()
                except queue.Empty:
                    break
                if line == "__PIPELINE_COMPLETE__":
                    complete = True
                    break
                st.session_state.log_lines.append(line)

            # Show the tail of the log.
            tail = st.session_state.log_lines[-400:]
            log_box.code("\n".join(tail) if tail else "Starting…", language="text")

            if complete:
                st.session_state.running = False
                status = st.session_state.result.get("status")
                if status == "error":
                    st.error(f"Pipeline failed: {st.session_state.result.get('error', 'unknown error')}")
                elif status == "stopped":
                    st.warning("Run stopped early. Partial results were saved to the output directory.")
                else:
                    st.success("Pipeline complete.")
                st.rerun()
            else:
                note = ("Stopping…" if st.session_state.stop_requested
                        else "Running… this page refreshes automatically.")
                progress_note.caption(note)
                time.sleep(1.0)
                st.rerun()


        # ---------------------------------------------------------------------
        # Results view (after a completed run)
        # ---------------------------------------------------------------------

        def show_results(out_dir: str) -> None:
            out = Path(out_dir)
            summary_path = out / "run_summary.json"
            if summary_path.exists():
                try:
                    summary = json.loads(summary_path.read_text())
                except Exception:
                    summary = {}

                st.markdown("#### Run summary")
                m = st.columns(4)
                m[0].metric("PMIDs retrieved", summary.get("pmids_retrieved", "—"))
                m[1].metric("Articles processed", summary.get("articles_processed_with_metadata", "—"))
                m[2].metric("RAG source", summary.get("rag_source", "—"))
                m[3].metric("RAG chunks", summary.get("rag_vector_db_chunks", "—"))

                with st.expander("Full run_summary.json"):
                    st.json(summary)

            # Publication TXT summary.
            txt_path = out / "publication_summary.txt"
            if txt_path.exists():
                txt = txt_path.read_text()
                st.markdown("#### Publication summary (TXT)")
                st.download_button(
                    "⬇  Download publication_summary.txt",
                    data=txt,
                    file_name="publication_summary.txt",
                    mime="text/plain",
                )
                with st.expander("Preview"):
                    st.code(txt[:8000] + ("\n…(truncated)" if len(txt) > 8000 else ""), language="text")

            # Data files for download + preview.
            st.markdown("#### Output files")
            file_specs = [
                ("metadata.parquet", "Article metadata"),
                ("cases.parquet", "Extracted text records"),
                ("captions.parquet", "Figure captions"),
                ("images.parquet", "Image records"),
            ]
            any_file = False
            for fname, label in file_specs:
                fpath = out / fname
                if not fpath.exists():
                    continue
                any_file = True
                cols = st.columns([2, 1])
                cols[0].write(f"**{label}** — `{fname}`")
                with open(fpath, "rb") as fh:
                    cols[1].download_button(
                        "Download", data=fh.read(), file_name=fname, key=f"dl_{fname}",
                        use_container_width=True,
                    )

            if not any_file:
                st.info("No output files found yet in this directory.")

            # Parsed Markdown files
            md_out = out / "parsed_markdown"
            if md_out.exists():
                md_files_found = sorted(md_out.glob("*.md"))
                if md_files_found:
                    st.markdown(
                        f"**Parsed Markdown** — `parsed_markdown/` "
                        f"({len(md_files_found)} files)"
                    )
                    with st.expander("List Markdown files"):
                        for mf in md_files_found:
                            st.write(f"- `{mf.name}`")

            # RAG vector database
            vdb_out = out / "vector_db"
            if vdb_out.exists() and (vdb_out / "index.faiss").exists():
                st.success(
                    f"RAG vector database ready at `{vdb_out}` — "
                    "loadable by `query_kb.py` / `app.py` without modification."
                )

            # Quick preview of the metadata table.
            meta_path = out / "metadata.parquet"
            if meta_path.exists():
                try:
                    df = pd.read_parquet(meta_path)
                    with st.expander(f"Preview metadata ({len(df)} rows)"):
                        st.dataframe(df.head(50), use_container_width=True)
                except Exception as e:
                    st.caption(f"Could not preview metadata: {e}")


        if not st.session_state.running and st.session_state.output_dir:
            out_dir = st.session_state.output_dir
            if Path(out_dir).exists():
                st.markdown('<hr class="pd-rule">', unsafe_allow_html=True)
                show_results(out_dir)

                if st.session_state.log_lines:
                    with st.expander("Show full run log"):
                        st.code("\n".join(st.session_state.log_lines), language="text")


    with tab2:
        st.markdown("### 💬 RAG Chatbot")
        st.markdown("#### 🔌 Load an existing PubVector RAG database")
        st.info(
            "Paste the folder path for a PubVector output directory or its `vector_db` directory, "
            "then click **Load RAG database and activate chatbot**. No new pipeline run is required."
        )

        def is_valid_vector_db(path: str | Path) -> bool:
            """Return True when `path` looks like a saved LangChain FAISS DB."""
            p = Path(path).expanduser()
            return p.is_dir() and (p / "index.faiss").exists()

        def resolve_pubvector_backend(folder_path: str | Path) -> tuple[Optional[dict], str]:
            """Resolve a user-provided folder to a FAISS chat backend.

            The user may give the vector_db folder itself, or a PubVector output
            folder that contains vector_db/. Returns (backend, error_message), where
            backend is {"type": "bioc", "vector_db_path": Path}.
            """
            raw_path = str(folder_path).strip()
            if not raw_path:
                return None, "Enter the folder location of a previously created PubVector RAG database."

            folder = Path(raw_path).expanduser()
            if not folder.exists():
                return None, f"Folder does not exist: {folder}"
            if not folder.is_dir():
                return None, f"Path is not a folder: {folder}"

            # Case 1: user gave the FAISS vector_db folder directly.
            if is_valid_vector_db(folder):
                return {"type": "bioc", "vector_db_path": folder}, ""

            # Case 2: user gave a PubVector output folder containing vector_db/.
            candidate = folder / "vector_db"
            if is_valid_vector_db(candidate):
                return {"type": "bioc", "vector_db_path": candidate}, ""

            return (
                None,
                "No usable RAG database was found at this location. "
                "Provide a PubVector output folder containing `vector_db/index.faiss`, "
                "or the `vector_db` folder itself.",
            )

        default_rag_folder = st.session_state.get("rag_database_folder_input", "")
        if not default_rag_folder:
            default_rag_folder = st.session_state.get("output_dir", "") or "./raredx_data"

        rag_folder_location = st.text_input(
            "RAG database folder location",
            value=default_rag_folder,
            placeholder="/path/to/pubvector_output or /path/to/pubvector_output/vector_db",
            help="Use a PubVector output folder, or paste the vector_db folder directly.",
            key="rag_database_folder_input",
        )

        load_rag_clicked = st.button(
            "Load RAG database and activate chatbot",
            type="primary",
            use_container_width=True,
            key="load_existing_rag_database_button",
        )

        if load_rag_clicked:
            backend, error = resolve_pubvector_backend(rag_folder_location)
            if error:
                st.error(error)
            elif backend is not None:
                backend_key = str(backend["vector_db_path"])
                if backend_key != st.session_state.get("active_backend_key", ""):
                    st.session_state.chat_messages = []
                st.session_state.active_backend_key = backend_key
                st.session_state.active_backend = backend
                st.session_state.active_pubvector_output_dir = (
                    str(backend["vector_db_path"].parent)
                    if backend["vector_db_path"].name == "vector_db"
                    else str(backend["vector_db_path"])
                )
                st.session_state.create_chatbot = True
                st.success("Loaded FAISS RAG database.")
                st.rerun()

        backend = st.session_state.get("active_backend")

        if not backend:
            st.markdown(
                '<div class="pd-empty"><h3>No knowledge base loaded yet</h3>'
                'Paste a PubVector output folder above and click '
                '<b>Load RAG database and activate chatbot</b>.<br>'
                'No database yet? Build one in the <b>Pipeline</b> tab first.</div>',
                unsafe_allow_html=True,
            )
            st.stop()

        if not is_valid_vector_db(backend["vector_db_path"]):
            st.error(
                "The active path is not a valid FAISS vector database folder. "
                "Choose a PubVector output folder that contains `vector_db/index.faiss`."
            )
            st.session_state.active_backend = None
            st.stop()

        # Sidebar controls for the chatbot.
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 💬 Chatbot settings")
            models = list_ollama_models()
            if models:
                remembered = cfg.get("ollama_model", OLLAMA_CHAT_MODEL)
                default_idx = models.index(remembered) if remembered in models else 0
                ollama_model = st.selectbox(
                    "Ollama model",
                    options=models,
                    index=default_idx,
                    help="Auto-detected from your running Ollama. "
                         "Pull more with `ollama pull <model>`.",
                )
                if ollama_model != cfg.get("ollama_model"):
                    save_user_config({"ollama_model": ollama_model})
                    cfg["ollama_model"] = ollama_model
            else:
                st.warning(
                    "No Ollama models detected. Start Ollama with `ollama serve` "
                    "and pull one, e.g. `ollama pull medgemma:latest`, then reload."
                )
                ollama_model = st.text_input(
                    "Ollama model",
                    value=OLLAMA_CHAT_MODEL,
                    help="Ollama model tag to use, e.g. medgemma:latest",
                )

            # Only models that advertise the capability can think.
            if model_supports_thinking(ollama_model):
                enable_thinking = st.checkbox(
                    "🧠 Thinking",
                    value=False,
                    help="Let the model reason step-by-step before answering.",
                )
                if enable_thinking:
                    st.warning(
                        "Thinking makes each answer noticeably slower and uses more "
                        "VRAM — the model generates a separate reasoning pass first.",
                        icon="⏳",
                    )
            else:
                enable_thinking = False

            top_k = st.slider(
                "Retrieved documents (k)",
                min_value=1, max_value=20, value=5,
                help="Number of context chunks retrieved per query.",
            )
            if st.button("🗑  Clear chat history", key="clear_chat"):
                st.session_state.chat_messages = []
                st.rerun()

        @st.cache_resource(show_spinner="Loading vector database…")
        def _get_vectorstore(path: str, device: str = "cpu"):
            return load_chat_vector_db(path, device=device)

        vdb_path = str(backend["vector_db_path"])
        vectorstore = _get_vectorstore(vdb_path)
        if vectorstore is None:
            st.error(
                "Failed to load the vector database. "
                "Check that the RAG dependencies are installed and the index is compatible. "
                "Expected LangChain FAISS files such as `index.faiss` and `index.pkl`."
            )
            st.stop()
        retrieve_docs_fn = lambda query, k: vectorstore.similarity_search(query, k=k)
        embedding_label = read_embedding_model(vdb_path)
        chunk_label = read_chunk_config(vdb_path)
        db_label = f"Vector DB: `{vdb_path}`"
        retrieval_label = "Vector RAG (FAISS)"

        active_output_dir = st.session_state.get("active_pubvector_output_dir", "")
        st.success("Chatbot is ready.")
        st.caption(
            f"PubVector folder: `{active_output_dir}` &nbsp;·&nbsp; "
            f"{db_label} &nbsp;·&nbsp; "
            f"Embeddings: `{embedding_label}` &nbsp;·&nbsp; "
            f"Chunks: `{chunk_label}` &nbsp;·&nbsp; "
            f"Retrieval: `{retrieval_label}` &nbsp;·&nbsp; "
            f"Model: `{ollama_model}` &nbsp;·&nbsp; "
            f"Retrieval k={top_k}"
        )
        st.markdown('<hr class="pd-rule">', unsafe_allow_html=True)

        def render_sources(sources: list[dict]) -> None:
            """Render retrieved chunks with clickable PubMed/PMC/DOI links."""
            for src in sources:
                # PMCID falls back to the source filename (e.g. PMC12345.json/.md).
                pmcid = src.get("pmcid") or ""
                if not pmcid:
                    stem = src.get("source", "").split(".")[0]
                    if stem.startswith("PMC"):
                        pmcid = stem
                links = []
                if pmcid:
                    links.append(
                        f"[PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/)"
                    )
                if src.get("pmid"):
                    links.append(
                        f"[PubMed](https://pubmed.ncbi.nlm.nih.gov/{src['pmid']}/)"
                    )
                if src.get("doi"):
                    links.append(f"[DOI](https://doi.org/{src['doi']})")

                label = src.get("title") or src.get("source") or pmcid or "source"
                meta = " · ".join(
                    x for x in [
                        f"Section: {src['section']}" if src.get("section") else "",
                        src.get("chunk_kind", ""),
                    ] if x
                )
                line = f"**{label}**"
                if links:
                    line += "  \n" + " · ".join(links)
                if meta:
                    line += f" — {meta}"
                st.markdown(line)
                st.caption(src["content"][:500])

        # Render chat history.
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander("Retrieved context & sources"):
                        render_sources(msg["sources"])

        # Suggested starter questions when the conversation is empty. A click
        # routes through the same handler as a typed query via pending_query.
        pending = st.session_state.pop("pending_query", None)
        if not st.session_state.chat_messages and pending is None:
            st.caption("Try one of these to get started:")
            starters = [
                "What are the key clinical features?",
                "How is this condition diagnosed?",
                "What treatment options are described?",
            ]
            for col, q in zip(st.columns(len(starters)), starters):
                if col.button(q, key=f"starter_{q}", use_container_width=True):
                    st.session_state.pending_query = q
                    st.rerun()

        # Chat input.
        typed = st.chat_input(
            "Ask a clinical question about the selected knowledge base…"
        )
        if user_query := (typed or pending):
            st.session_state.chat_messages.append(
                {"role": "user", "content": user_query}
            )
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                with st.status(
                    "Searching knowledge base…", expanded=False
                ) as _status:
                    docs    = retrieve_docs_fn(user_query, top_k)
                    context = _format_chat_context(docs)
                    sources = [
                        {
                            "source": d.metadata.get("source", ""),
                            "rag_source": d.metadata.get("rag_source", ""),
                            "pmcid": d.metadata.get("pmcid", ""),
                            "pmid": d.metadata.get("pmid", ""),
                            "doi": d.metadata.get("doi", ""),
                            "title": d.metadata.get("title", ""),
                            "section": d.metadata.get("section", ""),
                            "section_type": d.metadata.get("section_type", ""),
                            "chunk_kind": d.metadata.get("chunk_kind", ""),
                            "passage_index": d.metadata.get("passage_index", ""),
                            "chunk_id": d.metadata.get("chunk_id", ""),
                            "content": d.page_content,
                        }
                        for d in docs
                    ]
                    history = [
                        m for m in st.session_state.chat_messages[:-1]
                        if m["role"] in ("user", "assistant")
                    ]
                    prompt   = _build_rag_prompt(user_query, context, history)
                    _status.update(label="Retrieved context", state="complete")

                # Stream the answer so words appear as the model generates them.
                # The first token can take a while if Ollama is loading the model,
                # so always show progress and a clear fallback if nothing comes back.
                think_box   = st.empty()   # live reasoning, only when thinking is on
                placeholder = st.empty()
                placeholder.markdown(f"_Generating with {ollama_model}…_")
                response = ""
                thinking = ""
                for kind, piece in _stream_ollama(
                    prompt, model=ollama_model, think=enable_thinking
                ):
                    if kind == "thinking":
                        thinking += piece
                        think_box.markdown(f"🧠 _Thinking…_\n\n> {thinking.strip()}")
                    else:
                        response += piece
                        placeholder.markdown(response + " ▌")
                if thinking.strip():
                    think_box.empty()
                    with think_box.expander("🧠 Model reasoning"):
                        st.markdown(thinking.strip())
                if response.strip():
                    placeholder.markdown(response)
                elif thinking.strip():
                    response = (
                        "_The model used its entire token budget reasoning and never "
                        "reached an answer. Try a larger model, or turn off "
                        "**🧠 Thinking** for a direct reply._"
                    )
                    placeholder.markdown(response)
                else:
                    response = (
                        "_No response from the model. It may still be loading — "
                        "try again. If it persists, check that `ollama serve` is "
                        f"running and that `{ollama_model}` is pulled._"
                    )
                    placeholder.markdown(response)
                with st.expander("Retrieved context & sources"):
                    render_sources(sources)

            st.session_state.chat_messages.append(
                {
                    "role":    "assistant",
                    "content": response,
                    "sources": sources,
                }
            )

# ---------------------------------------------------------------------
# Unified entry point: Streamlit app vs command-line pipeline
# ---------------------------------------------------------------------

def _running_under_streamlit() -> bool:
    """True if this script is being executed by `streamlit run`."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if _running_under_streamlit():
    # Launched via `streamlit run pubvector.py` -> render the web UI.
    run_app()
elif __name__ == "__main__":
    # Launched via `python pubvector.py ...` -> run the CLI pipeline.
    raise SystemExit(main())