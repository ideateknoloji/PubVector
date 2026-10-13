# PubVector Baseline LLM Question Set

These are the **no-context baseline** prompts for the PubVector evaluation. Run each one through the **web app** of every baseline model (Gemini, ChatGPT, Claude) and collect the answers.

## How to run

1. For **each** question below, open a **fresh chat** in the model's web app (a new conversation per question — do not let earlier answers leak into later ones).
2. Copy the entire code block for that question and paste it as your message.
3. Copy the model's **full** answer back, labelled with the question **ID** (e.g. `FAB-F-01`) and the model name.
4. Repeat for all 3 models.

> The standard instruction is baked into every block, so each block is a complete, self-contained prompt. **Do not** add the gold answer or any hints — these are no-context baselines.

- **Questions:** 120  ·  **Models:** Gemini, ChatGPT, Claude  ·  **Total runs:** 360

## Contents

- [Fabry Disease](#fabry-disease)
- [Lung Adenocarcinoma](#lung-adenocarcinoma)
- [CTX](#ctx)
- [Single Cell RNA Sequencing](#single-cell-rna-sequencing)


## Fabry Disease

### Factual tier

#### `FAB-F-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What gene is mutated in Fabry disease?
```

#### `FAB-F-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What enzyme is deficient in Fabry disease and what substrate does it fail to break down?
```

#### `FAB-F-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the inheritance pattern of Fabry disease?
```

#### `FAB-F-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How is Fabry disease diagnosed in males versus females?
```

#### `FAB-F-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the name of the characteristic eye finding in Fabry disease?
```

#### `FAB-F-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What class of lysosomal storage disorder is Fabry disease, and what lipid accumulates in vascular endothelium and other tissues?
```

#### `FAB-F-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Which biomarker is commonly elevated in classic Fabry disease and is especially useful for disease burden assessment?
```

#### `FAB-F-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the typical renal manifestation of Fabry disease before advanced chronic kidney disease develops?
```

#### `FAB-F-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What cardiac phenotype is classically associated with Fabry disease in adults?
```

#### `FAB-F-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the difference between classic Fabry disease and later-onset Fabry disease at the level of residual alpha-galactosidase A activity?
```

### Clinical tier

#### `FAB-C-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the characteristic early symptoms of Fabry disease in childhood and adolescence?
```

#### `FAB-C-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Which organ systems are most severely affected in classic Fabry disease in adulthood, and what are the leading causes of death?
```

#### `FAB-C-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is lyso-Gb3 and why is it clinically important in Fabry disease?
```

#### `FAB-C-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the two approved enzyme replacement therapy (ERT) products for Fabry disease, how are they administered, and what are their differences?
```

#### `FAB-C-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is migalastat and for which Fabry patients is it appropriate?
```

#### `FAB-C-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should a newly diagnosed adult with Fabry disease be evaluated at baseline before deciding on disease-specific therapy?
```

#### `FAB-C-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What clinical features should prompt Fabry disease testing in a patient with otherwise unexplained hypertrophic cardiomyopathy?
```

#### `FAB-C-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How do Fabry disease manifestations differ between hemizygous males and heterozygous females, and why can females be severely affected?
```

#### `FAB-C-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What supportive treatments are commonly used alongside disease-specific therapy in Fabry disease?
```

#### `FAB-C-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should family screening and genetic counselling be approached after identifying a pathogenic GLA variant in a proband?
```

### Synthesis tier

#### `FAB-S-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should the decision to initiate enzyme replacement therapy (ERT) be personalised for a 28-year-old female with Fabry disease who has a non-amenable GLA mutation, mild neuropathic pain, and no organ damage on workup?
```

#### `FAB-S-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Why does ERT appear less effective when started after significant organ damage has already occurred in Fabry disease, and what does this imply for newborn screening?
```

#### `FAB-S-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How do the diagnostic and management challenges of Fabry disease differ between classic and late-onset phenotypes?
```

#### `FAB-S-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the limitations of the available evidence for ERT efficacy in Fabry disease, and what would stronger evidence require?
```

#### `FAB-S-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A male patient on agalsidase beta develops persistent anti-drug antibodies (ADAs). How should this be managed and what are the clinical implications?
```


#### `FAB-S-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A 45-year-old man with Fabry disease has progressive left ventricular hypertrophy, reduced renal function, and neuropathic pain despite late initiation of ERT. How should therapeutic expectations and monitoring be framed?
```

#### `FAB-S-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should clinicians interpret a GLA variant of uncertain significance in a patient with mild left ventricular hypertrophy and borderline lyso-Gb3 elevation?
```

#### `FAB-S-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the trade-offs between ERT and migalastat when treating an adult with Fabry disease and an amenable GLA variant?
```

#### `FAB-S-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should Fabry disease management be adapted during pregnancy or pregnancy planning?
```

#### `FAB-S-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Design a pragmatic monitoring plan for an adult Fabry patient receiving disease-specific therapy, including renal, cardiac, neurological, and biochemical endpoints.
```

## Lung Adenocarcinoma

### Factual tier

#### `LAC-F-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the most common actionable driver mutation in lung adenocarcinoma in never-smokers?
```

#### `LAC-F-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the standard first-line targeted therapy for metastatic EGFR-mutant (exon 19 del or L858R) lung adenocarcinoma?
```

#### `LAC-F-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What PD-L1 tumour proportion score (TPS) threshold is required for pembrolizumab monotherapy as first-line treatment in metastatic lung adenocarcinoma without a driver mutation?
```

#### `LAC-F-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Which specific mutation makes lung adenocarcinoma resistant to standard EGFR TKIs and requires a different therapeutic approach?
```

#### `LAC-F-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the recommended molecular testing approach for newly diagnosed metastatic lung adenocarcinoma?
```

#### `LAC-F-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Which major actionable alterations should be included in molecular testing for metastatic non-squamous NSCLC?
```

#### `LAC-F-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is an ALK rearrangement in lung adenocarcinoma, and what class of drugs targets it?
```

#### `LAC-F-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the preferred first-line targeted therapy for metastatic ALK-positive lung adenocarcinoma?
```

#### `LAC-F-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is MET exon 14 skipping, and why is it clinically actionable in lung adenocarcinoma?
```

#### `LAC-F-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the usual histologic marker profile used to support a diagnosis of lung adenocarcinoma on immunohistochemistry?
```

### Clinical tier

#### `LAC-C-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How does stage at diagnosis determine treatment approach in lung adenocarcinoma? Summarise the strategy for stages I-II, III, and IV.
```

#### `LAC-C-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What resistance mechanisms commonly develop to first-line osimertinib in EGFR-mutant lung adenocarcinoma, and how is resistance detected?
```

#### `LAC-C-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the key clinical features and histological characteristics that distinguish lung adenocarcinoma from other NSCLC subtypes?
```

#### `LAC-C-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How is KRAS G12C-mutant lung adenocarcinoma now managed, and how does this differ from other KRAS mutations?
```

#### `LAC-C-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the role of liquid biopsy (ctDNA) in the clinical management of lung adenocarcinoma, and when should it be used rather than or alongside tissue biopsy?
```

#### `LAC-C-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should brain metastases influence treatment selection in oncogene-driven metastatic lung adenocarcinoma?
```

#### `LAC-C-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the role of maintenance therapy after first-line platinum-based chemotherapy for metastatic lung adenocarcinoma without actionable drivers?
```

#### `LAC-C-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should oligometastatic lung adenocarcinoma be managed differently from widely metastatic disease?
```

#### `LAC-C-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the major immune-related adverse events of checkpoint inhibitors used in lung adenocarcinoma, and how should they be recognised clinically?
```

#### `LAC-C-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: When is repeat biopsy recommended in lung adenocarcinoma, and what information can it provide beyond initial diagnosis?
```

### Synthesis tier

#### `LAC-S-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A 55-year-old never-smoking Asian woman presents with metastatic lung adenocarcinoma. NGS shows EGFR exon 19 deletion and PD-L1 TPS of 60%. Should she receive osimertinib, pembrolizumab monotherapy, or combination chemo-immunotherapy? Justify your reasoning.
```

#### `LAC-S-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How has the approval of adjuvant osimertinib (ADAURA trial) changed the management of resected early-stage EGFR-mutant lung adenocarcinoma, and what are the remaining uncertainties?
```

#### `LAC-S-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Discuss the challenge of co-occurring genomic alterations in lung adenocarcinoma and how they complicate therapeutic decisions, using EGFR + ALK co-alteration as an example.
```

#### `LAC-S-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the evidence base for adding bevacizumab or ramucirumab to EGFR TKI therapy in EGFR-mutant lung adenocarcinoma, and for which patients might this be reasonable?
```

#### `LAC-S-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should a clinician approach a patient with lung adenocarcinoma and a MET exon 14 skipping mutation? What are the therapeutic options, expected responses, and common resistance patterns?
```


#### `LAC-S-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A patient with metastatic lung adenocarcinoma has high PD-L1 expression but an untreated ALK rearrangement. How should first-line therapy be selected and why?
```

#### `LAC-S-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should clinicians sequence targeted therapy, chemotherapy, and immunotherapy after progression on first-line osimertinib when no targetable resistance mutation is found?
```

#### `LAC-S-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Discuss how limited tissue availability should shape diagnostic prioritisation in newly diagnosed metastatic lung adenocarcinoma.
```

#### `LAC-S-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should perioperative systemic therapy be individualised for resectable lung adenocarcinoma when both PD-L1 expression and driver mutation status are relevant?
```

#### `LAC-S-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A patient with lung adenocarcinoma has discordant tissue NGS and plasma ctDNA results. How should this discrepancy be interpreted and managed?
```

## CTX

### Factual tier

#### `CTX-F-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What gene is mutated in cerebrotendinous xanthomatosis (CTX)?
```

#### `CTX-F-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What substance accumulates abnormally in CTX and in which tissues?
```

#### `CTX-F-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the inheritance pattern of CTX?
```

#### `CTX-F-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the current standard treatment for CTX and what biochemical effect does it have?
```

#### `CTX-F-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the hallmark clinical features of CTX (the four cardinal findings)?
```

#### `CTX-F-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Which enzyme is deficient in CTX, and what normal bile acid synthesis step is impaired?
```

#### `CTX-F-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What bile alcohol abnormalities are characteristic of CTX and how are they detected?
```

#### `CTX-F-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the typical age pattern of cataracts, diarrhoea, tendon xanthomas, and neurological disease in CTX?
```

#### `CTX-F-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What confirmatory genetic test is used after biochemical suspicion of CTX?
```

#### `CTX-F-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the relationship between cholesterol levels and cholestanol levels in CTX?
```

### Clinical tier

#### `CTX-C-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What biochemical tests are used to diagnose CTX, and which is the most reliable screening test?
```

#### `CTX-C-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What neurological manifestations are seen in untreated CTX, and what does brain MRI typically show?
```

#### `CTX-C-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How does the age at treatment initiation affect outcomes in CTX?
```

#### `CTX-C-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Why is CTX thought to be substantially underdiagnosed, and what conditions is it most often confused with?
```

#### `CTX-C-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should plasma cholestanol be used to monitor treatment response in CTX patients on CDCA?
```

#### `CTX-C-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What early-life clinical clues should trigger suspicion for CTX before neurological disability becomes established?
```

#### `CTX-C-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should tendon xanthomas be evaluated when CTX is in the differential diagnosis?
```

#### `CTX-C-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the expected biochemical and clinical responses after starting chenodeoxycholic acid in CTX?
```

#### `CTX-C-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should adherence, dosing, and safety monitoring be handled for long-term CDCA therapy in CTX?
```

#### `CTX-C-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the role of cascade testing for siblings and relatives after a CTX diagnosis?
```

### Synthesis tier

#### `CTX-S-01`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Explain the metabolic mechanism by which CYP27A1 deficiency leads to cholestanol accumulation and the rationale for CDCA as treatment.
```

#### `CTX-S-02`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A 35-year-old patient is diagnosed with CTX and starts CDCA therapy. After 12 months, plasma cholestanol has normalised, but neurological symptoms (mild ataxia and slowed cognition) have not improved. How should you counsel the patient and what adjustments, if any, should be considered?
```

#### `CTX-S-03`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should CTX be distinguished from other inherited conditions causing tendon xanthomas and neurological disease?
```

#### `CTX-S-04`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the rationale for newborn or childhood screening for CTX, and what are the practical challenges?
```

#### `CTX-S-05`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Beyond CDCA, what other therapeutic approaches have been investigated for CTX, and what are the limitations of the current standard of care?
```

#### `CTX-S-06`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A teenager has bilateral juvenile cataracts, chronic diarrhoea, subtle learning difficulties, and no tendon xanthomas. How should CTX be evaluated despite incomplete cardinal features?
```

#### `CTX-S-07`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should clinicians distinguish irreversible neurological injury from insufficient biochemical control in a CTX patient treated with CDCA?
```

#### `CTX-S-08`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What would an effective CTX screening strategy need to balance analytically, clinically, and economically?
```

#### `CTX-S-09`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should treatment priorities differ between an asymptomatic genetically diagnosed child and a symptomatic adult with long-standing CTX?
```

#### `CTX-S-10`

```text
You are an expert medical AI assistant specialising in rare diseases and oncology. Answer the following clinical question concisely and precisely, using established medical knowledge. Use clear headings where relevant (e.g. Pathophysiology, Clinical Features, Diagnosis, Treatment), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Critically appraise the evidence base for CDCA in CTX and explain what outcomes future studies should measure.
```

## Single Cell RNA Sequencing

### Factual tier

#### `SCRNA-F-01`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is single-cell RNA sequencing (scRNA-seq), and what biological information does it measure?
```

#### `SCRNA-F-02`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the difference between droplet-based and plate-based scRNA-seq methods?
```

#### `SCRNA-F-03`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are UMIs in scRNA-seq, and why are they important for quantification?
```

#### `SCRNA-F-04`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is the main difference between 3-prime and full-length scRNA-seq protocols?
```

#### `SCRNA-F-05`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is a cell barcode, and how does it differ from a UMI?
```

#### `SCRNA-F-06`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are common quality-control metrics used to filter low-quality cells in scRNA-seq data?
```

#### `SCRNA-F-07`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is dimensionality reduction in scRNA-seq analysis, and why are PCA, UMAP, or t-SNE commonly used?
```

#### `SCRNA-F-08`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is clustering in scRNA-seq, and what does a cluster usually represent biologically?
```

#### `SCRNA-F-09`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are marker genes, and how are they used to annotate cell types in scRNA-seq datasets?
```

#### `SCRNA-F-10`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is doublet contamination in scRNA-seq, and why does it matter?
```

### Clinical tier

#### `SCRNA-C-01`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should scRNA-seq data be preprocessed from raw sequencing reads to a cell-by-gene expression matrix?
```

#### `SCRNA-C-02`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should mitochondrial RNA percentage, detected gene count, and total UMI count be interpreted during scRNA-seq quality control?
```

#### `SCRNA-C-03`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the major sources of batch effect in scRNA-seq studies, and how can they be mitigated?
```

#### `SCRNA-C-04`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should cell-type annotation be performed and validated in a heterogeneous tumour scRNA-seq dataset?
```

#### `SCRNA-C-05`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How can scRNA-seq be used to distinguish malignant epithelial cells from non-malignant epithelial cells in cancer samples?
```

#### `SCRNA-C-06`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is differential gene expression analysis in scRNA-seq, and what pitfalls arise from treating individual cells as independent replicates?
```

#### `SCRNA-C-07`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What is pseudobulk analysis, and when is it preferable to cell-level differential expression testing?
```

#### `SCRNA-C-08`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How can scRNA-seq be used to infer immune-cell states such as exhaustion, activation, or regulatory phenotypes?
```

#### `SCRNA-C-09`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are ligand-receptor interaction analyses in scRNA-seq, and what biological and statistical caveats should be considered?
```

#### `SCRNA-C-10`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should scRNA-seq findings be validated experimentally before drawing clinical or mechanistic conclusions?
```

### Synthesis tier

#### `SCRNA-S-01`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A tumour scRNA-seq dataset shows a small cluster expressing both T-cell and epithelial markers. How should this finding be interpreted and investigated?
```

#### `SCRNA-S-02`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How would you design an scRNA-seq study to compare pre-treatment and post-treatment tumour biopsies from patients receiving immunotherapy?
```

#### `SCRNA-S-03`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: A rare cell population appears only after batch correction. How would you determine whether it is biologically real or an integration artefact?
```

#### `SCRNA-S-04`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should scRNA-seq and bulk RNA-seq be integrated to identify clinically relevant tumour microenvironment signatures?
```

#### `SCRNA-S-05`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the trade-offs between profiling more cells per sample versus more biological replicates in a clinical scRNA-seq study?
```

#### `SCRNA-S-06`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should a clinician or translational researcher interpret pathway enrichment results derived from scRNA-seq clusters?
```

#### `SCRNA-S-07`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How can scRNA-seq contribute to biomarker discovery in oncology, and what barriers limit direct clinical implementation?
```

#### `SCRNA-S-08`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: What are the strengths and limitations of using scRNA-seq to reconstruct differentiation trajectories or disease progression?
```

#### `SCRNA-S-09`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: How should multimodal single-cell data, such as CITE-seq or single-cell ATAC plus RNA, be used to refine cell-state interpretation?
```

#### `SCRNA-S-10`

```text
You are an expert biomedical AI assistant specialising in genomics, transcriptomics, rare diseases and oncology. Answer the following clinical or scientific question concisely and precisely, using established biomedical knowledge. Use clear headings where relevant (e.g. Concept, Workflow, Interpretation, Limitations), and include only sections that are relevant to the question. If you are uncertain or the answer is not well established, say so rather than speculating.

Question: Critically appraise the reproducibility challenges in scRNA-seq studies and propose practices that would make results more robust and clinically actionable.
```

