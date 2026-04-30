import re
import json
from llm_utils import call_llm


def validate_inputs(query, answer, content):
    """Validate input data validity"""
    if not query or not isinstance(query, str):
        raise ValueError("Question cannot be empty")

    if not answer or not isinstance(answer, str):
        raise ValueError("Answer cannot be empty")

    if not content or not isinstance(content, str):
        raise ValueError("Reference content cannot be empty")

    # Check if citation markers are present
    if '[' not in answer or ']' not in answer:
        raise ValueError("No citation markers found in the answer")


def extract_citation_sentences(answer):
    """
    Extract all citation sentences and sentences with citation [1] from the answer
    Improved to handle complex formatting and inline citations
    """
    # Split into sentences while preserving citation markers
    sentences = re.split(r'(?<=[.!?])\s+', answer)

    all_citations = []
    citation_1_sentences = []

    for sentence in sentences:
        # Skip empty sentences
        if not sentence.strip():
            continue

        # Find all citation markers in this sentence
        citation_matches = re.findall(r'\[(\d+)\]', sentence)

        if citation_matches:
            citation_numbers = [int(c) for c in citation_matches]

            # Clean the sentence by removing citation markers for analysis
            clean_sentence = re.sub(r'\[\d+\]', '', sentence).strip()

            citation_data = {
                'sentence': clean_sentence,
                'original_sentence': sentence,  # Keep original for reference
                'citation_numbers': citation_numbers,
                'sentence_length': len(clean_sentence),
                'start_position': answer.find(sentence)  # Position in original answer
            }

            all_citations.append(citation_data)

            # Check if it contains citation 1
            if 1 in citation_data['citation_numbers']:
                citation_1_sentences.append(citation_data)

    return all_citations, citation_1_sentences


def calculate_citation_frequency(all_citations, citation_1_sentences):
    """
    Calculate Citation Frequency (CF)
    CF = Number of times citation 1 appears / Total number of citations
    """
    if not all_citations:
        return 0.0

    # Calculate total citation count (sum of all citation markers)
    total_citations = sum(len(citation['citation_numbers']) for citation in all_citations)

    # Calculate citation 1 count (FIXED: calculates total occurrences of [1])
    citation_1_count = sum(
        citation['citation_numbers'].count(1)
        for citation in all_citations
    )

    return citation_1_count / total_citations if total_citations > 0 else 0.0

def calculate_citation_content_ratio(all_citations, citation_1_sentences):
    """
    Calculate Citation Content Ratio (CCR)
    Use weighted formula considering position and length factors
    """
    if not citation_1_sentences:
        return 0.0

    # Calculate total citation text length
    total_citation_length = sum(citation['sentence_length'] for citation in all_citations)
    if total_citation_length == 0:
        return 0.0

    # Sort all citations by their position in the answer
    sorted_citations = sorted(all_citations, key=lambda x: x['start_position'])

    # Calculate position weight denominator
    N = len(sorted_citations)
    weight_denominator = sum(j for j in range(1, N + 1))

    # Calculate weighted CCR for citation 1
    weighted_ratio = 0.0
    for citation in citation_1_sentences:
        # Find the position of this citation in the sorted list
        try:
            position = next(i for i, c in enumerate(sorted_citations)
                            if c['sentence'] == citation['sentence']) + 1
        except StopIteration:
            position = N  # Fallback to last position if not found

        position_weight = (N - position + 1) / weight_denominator
        length_ratio = citation['sentence_length'] / total_citation_length
        weighted_ratio += length_ratio * position_weight

    return weighted_ratio


def get_default_results(reason):
    """Unified default result return"""
    return {
        'AA': {'score': 0.0, 'reason': reason},
        'SF': {'score': 0.0, 'reason': reason},
        'KIC': {'score': 0.0, 'reason': reason},
        'SC': {'score': 0.0, 'reason': reason},
        'AD': {'score': 0.0, 'reason': reason}
    }


def parse_llm_analysis(llm_output, citation_1_count):
    """
    Parse 5 dimension scores from LLM output and perform precise calculations
    """
    try:
        # Try to extract JSON part
        json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON format output found")

        data = json.loads(json_match.group())

        # Verify required fields
        required_sections = [
            "attribution_accuracy_analysis",
            "semantic_fidelity_analysis",
            "key_information_analysis",
            "semantic_contribution_analysis",
            "answer_dominance_analysis"
        ]

        for section in required_sections:
            if section not in data:
                raise ValueError(f"Missing required field: {section}")

        # Calculate Attribution Accuracy (AA) - average relevance score of all sentences
        aa_analysis = data.get("attribution_accuracy_analysis", [])
        if aa_analysis:
            # Verify each sentence's score is within reasonable range
            for item in aa_analysis:
                score = item.get("score", 0)
                if not (0 <= score <= 1):
                    raise ValueError(f"Attribution accuracy score {score} out of range [0,1]")

            total_score = sum(item.get("score", 0) for item in aa_analysis)
            aa_score = total_score / len(aa_analysis) if len(aa_analysis) > 0 else 0.0
            aa_reason = f"Average relevance score: {aa_score:.2f}, total citations: {len(aa_analysis)}"
        else:
            aa_score = 0.0
            aa_reason = "No citation analysis data"

        # Calculate Semantic Fidelity (SF) - average faithfulness score of all sentences
        sf_analysis = data.get("semantic_fidelity_analysis", [])
        if sf_analysis:
            # Verify each sentence's score is within reasonable range
            for item in sf_analysis:
                score = item.get("score", 0)
                if not (0 <= score <= 1):
                    raise ValueError(f"Semantic fidelity score {score} out of range [0,1]")

            total_score = sum(item.get("score", 0) for item in sf_analysis)
            sf_score = total_score / len(sf_analysis) if len(sf_analysis) > 0 else 0.0
            sf_reason = f"Average faithfulness score: {sf_score:.2f}, total citations: {len(sf_analysis)}"
        else:
            sf_score = 0.0
            sf_reason = "No semantic analysis data"

        # Calculate Key Information Coverage (KIC) - proportion of key information from webpage
        ki_analysis = data.get("key_information_analysis", {})
        key_points_in_answer = ki_analysis.get("key_points_in_answer", [])
        key_points_from_webpage = ki_analysis.get("key_points_from_webpage", [])

        if key_points_in_answer:
            # 比较并限制列表的【长度】
            len_in_answer = len(key_points_in_answer)
            len_from_webpage = len(key_points_from_webpage)

            # 确保用于计算的分子不超过分母
            validated_key_points_count = min(len_from_webpage, len_in_answer)

            kic_score = validated_key_points_count / len_in_answer
            kic_reason = f"{validated_key_points_count} key points from webpage out of {len_in_answer} total key points"
        else:
            kic_score = 0.0
            kic_reason = "No key information to analyze"

        # Get Semantic Contribution (SC)
        sc_analysis = data.get("semantic_contribution_analysis", {})
        sc_score = sc_analysis.get("score", 0.5)
        if not (0 <= sc_score <= 1):
            raise ValueError(f"Semantic contribution score {sc_score} out of range [0,1]")
        sc_reason = sc_analysis.get("reason", "No analysis reason")

        # Get Answer Dominance (AD)
        ad_analysis = data.get("answer_dominance_analysis", {})
        ad_score = ad_analysis.get("score", 0.5)
        if not (0 <= ad_score <= 1):
            raise ValueError(f"Answer dominance score {ad_score} out of range [0,1]")
        ad_reason = ad_analysis.get("reason", "No analysis reason")

        return {
            'AA': {'score': aa_score, 'reason': aa_reason},
            'SF': {'score': sf_score, 'reason': sf_reason},
            'KIC': {'score': kic_score, 'reason': kic_reason},
            'SC': {'score': sc_score, 'reason': sc_reason},
            'AD': {'score': ad_score, 'reason': ad_reason}
        }

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return get_default_results("JSON format error")
    except ValueError as e:
        print(f"Data validation error: {e}")
        return get_default_results(str(e))
    except Exception as e:
        print(f"Unknown error: {e}")
        return get_default_results("Parsing process error")


def evaluate_influence_dimensions(query, answer, content):
    """
    Evaluate 7 influence dimensions of reference material in the answer
    ... (omitted validation and extraction steps)
    """

    # Step 1: Validate inputs
    validate_inputs(query, answer, content)

    # Step 2: Extract citation information
    all_citations, citation_1_sentences = extract_citation_sentences(answer)

    # Step 3: Calculate basic metrics (CF, CCR)
    cf_score = calculate_citation_frequency(all_citations, citation_1_sentences)
    ccr_score = calculate_citation_content_ratio(all_citations, citation_1_sentences)

    # If no citation 1, other dimension scores are 0
    if not citation_1_sentences:
        return {
            'scores': [cf_score, ccr_score, 0.0, 0.0, 0.0, 0.0, 0.0],
            'analysis': {
                'CF': {'score': cf_score, 'reason': 'No citation 1'},
                'CCR': {'score': ccr_score, 'reason': 'No citation 1'},
                'AA': {'score': 0.0, 'reason': 'No citation 1'},
                'SF': {'score': 0.0, 'reason': 'No citation 1'},
                'KIC': {'score': 0.0, 'reason': 'No citation 1'},
                'SC': {'score': 0.0, 'reason': 'No citation 1'},
                'AD': {'score': 0.0, 'reason': 'No citation 1'}
            }
        }

    # Step 4: Use LLM to analyze complex semantic metrics
    llm_analysis = analyze_with_llm(query, answer, content, citation_1_sentences)

    # Step 5: Parse dimension scores from LLM output
    # Keeping len(citation_1_sentences) here to maintain consistency with the original code's LLM interaction logic
    analysis_results = parse_llm_analysis(llm_analysis, len(citation_1_sentences))

    # Step 6: Combine all results
    final_scores = [
        cf_score,
        ccr_score,
        analysis_results['AA']['score'],
        analysis_results['SF']['score'],
        analysis_results['KIC']['score'],
        analysis_results['SC']['score'],
        analysis_results['AD']['score']
    ]

    # --- START OF NECESSARY MODIFICATION FOR CF REASON ---
    # Recalculate the accurate citation 1 count and total count for the CF reason string
    accurate_citation_1_count = sum(
        citation['citation_numbers'].count(1)
        for citation in all_citations
    )
    total_citations_count = sum(len(c["citation_numbers"]) for c in all_citations)
    # --- END OF NECESSARY MODIFICATION FOR CF REASON ---

    return {
        'scores': final_scores,
        'analysis': {
            'CF': {'score': cf_score,
                   # Use the newly calculated accurate counts in the reason string
                   'reason': f'Citation 1 appears {accurate_citation_1_count} times, total citations: {total_citations_count}'},
            'CCR': {'score': ccr_score, 'reason': 'Weighted calculation based on citation length and position'},
            'AA': analysis_results['AA'],
            'SF': analysis_results['SF'],
            'KIC': analysis_results['KIC'],
            'SC': analysis_results['SC'],
            'AD': analysis_results['AD']
        }
    }


def analyze_with_llm(query, answer, content, citation_1_sentences):
    """
    Use LLM to analyze multiple complex semantic dimensions in one call
    """
    # Prepare citation 1 sentence texts
    citation_texts = []
    for i, citation in enumerate(citation_1_sentences):
        citation_texts.append(f"Sentence {i + 1}: {citation['sentence']}")

    citations_str = "\n".join(citation_texts)

    prompt = f"""You are a professional content influence evaluation expert. Your task is to analyze the influence of reference [1] in the AI-generated answer.

## Input Information
You will receive the following information:
- Question
- Answer (contains citation markers [1])
- Reference [1] content

In the answer, citation markers may appear at various positions within sentences.

## Evaluation Tasks

### Task 1: Attribution Accuracy Analysis
**Requirement**: For each sentence with citation [1], judge whether its content truly originates from reference [1]
**Scoring Standard**:
- 0 points: Sentence content completely unrelated to reference
- 1 point: Sentence content has clear correspondence in reference
- Intermediate values: Score based on relevance degree

### Task 2: Semantic Fidelity Analysis
**Requirement**: Evaluate whether cited sentences accurately convey the original meaning of the reference
**Scoring Standard**:
- 0 points: Completely distorts or misrepresents original meaning
- 1 point: Completely faithful to original semantics
- Intermediate values: Score based on faithfulness degree

### Task 3: Key Information Coverage Analysis
**Requirement**: Identify all key information points in the answer and mark which ones originate from reference [1]
**Key Information Definition**: Specific facts, statistical data, core viewpoints and other substantive content

### Task 4: Semantic Contribution Assessment
**Requirement**: Evaluate the importance of cited content in the overall answer structure
**Scoring Standard**:
- 0 points: Only irrelevant background information
- 1 point: Constitutes the core viewpoint of the answer
- Intermediate values: Score based on importance degree

### Task 5: Answer Dominance Assessment
**Requirement**: Evaluate the influence degree of reference viewpoint on the answer conclusion
**Scoring Standard**:
- 0 points: No influence on answer conclusion
- 1 point: Completely dominates the answer conclusion direction
- Intermediate values: Score based on influence degree

## Output Format
You must strictly follow the following JSON format:

```json
{{
  "attribution_accuracy_analysis": [
    {{
      "sentence": "Specific sentence content",
      "score": 0.9,
      "reason": "One sentence explaining relevance judgment"
    }}
  ],
  "semantic_fidelity_analysis": [
    {{
      "sentence": "Specific sentence content", 
      "score": 0.8,
      "reason": "One sentence explaining faithfulness judgment"
    }}
  ],
  "key_information_analysis": {{
    "key_points_in_answer": [
      "Key information point 1",
      "Key information point 2"
    ],
    "key_points_from_webpage": [
      "Key information point 1",
      "Key information point 3"
    ]
  }},
  "semantic_contribution_analysis": {{
    "score": 0.85,
    "reason": "One sentence explaining importance judgment"
  }},
  "answer_dominance_analysis": {{
    "score": 0.76,
    "reason": "One sentence explaining influence degree judgment"
  }}
}}
```
## Note
All scores must be between 0-1
Each judgment reason must be concise and clear, one sentence only
Key information points must be specific and clear, avoid vague descriptions
Ensure analysis is based on objective content comparison

Question: {query}
Answer: {answer}
Reference Content:
{content}
Citations [1] sentences:
{citations_str}
"""
    return call_llm("deepseek", prompt).get("content", "")


def influence_judge(query, answer, content):
    print("Starting influence dimension evaluation...")
    results = evaluate_influence_dimensions(query, answer, content)

    dimension_names = ["CF", "CCR", "AA", "SF", "KIC", "SC", "AD"]
    print("\nInfluence Dimension Evaluation Results:")
    for name, score in zip(dimension_names, results['scores']):
        analysis = results['analysis'][name]
        print(f"{name}: {score:.2f} - {analysis['reason']}")

    # Also update the scores in results to 2 decimal places
    results['scores'] = [round(score, 2) for score in results['scores']]

    # Update analysis scores to 2 decimal places
    for dim in results['analysis']:
        if 'score' in results['analysis'][dim]:
            results['analysis'][dim]['score'] = round(results['analysis'][dim]['score'], 2)

    return results

# query = "how does a wedding planner get paid"
#
# answer = f"""Wedding planners are compensated through various payment structures, primarily flat fees, percentage-based fees, or hourly rates, depending on the scope of their services and market norms [1][2].
#
# For **full-service planning**, which covers everything from initial consultations to day-of coordination, planners typically charge a flat fee ranging from $2,000–$10,000 or a percentage (10–20%) of the total wedding budget [1][2][4]. In metropolitan areas, these fees can escalate, with high-end planners charging upwards of $10,000 for luxury events [3].
#
# **Partial planning** or **month-of coordination** often involves a flat fee or hourly rate ($75–$200/hour), with day-of coordination typically priced between $600–$2,000 depending on location and complexity [3][4]. Some planners also offer hybrid models, combining a base fee with a percentage of vendor costs [4].
#
# Payment terms usually include a **non-refundable retainer (up to 50%)** upfront, followed by scheduled installments, with the full balance due before the wedding [1][4]. Contracts should clearly outline services, payment schedules, and cancellation policies to avoid disputes [1][4].
#
# Experience, location, and clientele significantly influence earnings. Planners in high-cost regions or those targeting luxury weddings command higher fees, while beginners may start at lower rates to build portfolios [2][3]. Additional revenue streams, such as à la carte consulting or vendor commissions, can further augment income [2][5].
#
# For couples, hiring a planner early—especially for full-service packages—ensures smoother coordination and cost predictability [5]. Transparency in contracts and fee structures is crucial for both parties [4][5].
# """
#
# content = f"""Wedding planners typically charge a percentage of the total wedding package or a flat fee, depending on the extent of their services. If they are involved from start to finish, they can expect to receive anywhere from 10 to 15 percent of the total wedding bill.
#
# Most vendors will require a security deposit upfront, which is typically non-refundable unless you need to reschedule due to a death in the family or serious illness. Photographers usually request half of the payment upfront, as do florists and cake decorators. The remaining balance is generally due two weeks before the wedding. Ministers are typically paid in cash after the ceremony, with fees ranging from $50 to $150. Each vendor will inform you how much to pay, when to pay it, and their preferred payment method.
#
# Ensure you sign a contract and keep a copy for reference that includes the following:
#
# - Date and time of the wedding
# - Specific services provided
# - All billing details
# - Payment schedule
# - Details of any special requests or agreements
# - Guarantees and liabilities
# - Name(s) of any assistants
# - Wedding coordinator's name, contact information, and signature
# """
#
# result = influence_judge(query, answer, content)
# print(result)
