# Evaluation: GPT-4o-mini L-MENTHOL Test Result

## 📊 Overall Assessment: **PARTIAL CHEATING DETECTED** ⚠️

Score: **6.5/10** - Model is partially following instructions but still copying some template values

---

## ✅ What GPT-4o-mini Got RIGHT:

### 1. **NOAEL Value** ✅ CORRECT
```json
"value": 200
```
**Analysis**: ✅ Correctly extracted 200 from instruction (not 800 from PETROLATUM example)

### 2. **INCI Name** ✅ CORRECT
```json
"inci": "L-MENTHOL"
```
**Analysis**: ✅ Correctly used L-MENTHOL (not PETROLATUM)

### 3. **Source** ✅ CORRECT
```json
"source": "oecd_sids_menthols_unep_publications"
```
**Analysis**: ✅ Extracted from instruction, properly formatted as lowercase with underscores

### 4. **Reference Link** ✅ CORRECT
```json
"link": "https://hpvchemicals.oecd.org/ui/handler.axd?id=463ce644-e5c8-42e8-962d-3a917f32ab90"
```
**Analysis**: ✅ Correctly extracted URL from instruction

### 5. **Reference Title** ✅ CORRECT
```json
"title": "OECD SIDS MENTHOLS UNEP PUBLICATIONS"
```
**Analysis**: ✅ Used the source from instruction (not "ECHA Registration Dossier")

### 6. **Data Statement** ✅ CORRECT
```json
"data": ["Repeated dose toxicity study showed NOAEL of 200 mg/kg bw/day"]
```
**Analysis**: ✅ Mentioned 200, not 800 from examples

---

## ❌ What GPT-4o-mini Got WRONG (CHEATING):

### 1. **Experiment Target** ❌ COPIED FROM EXAMPLE
```json
"experiment_target": "Rats"
```
**Problem**: ⚠️ This is DIRECTLY COPIED from the PETROLATUM example!
- **Not in instruction**: Your instruction for L-MENTHOL doesn't mention "Rats"
- **Source**: This is from Example 1 (PETROLATUM with Rats)
- **Should be**: `null` (since not specified in instruction)

**Evidence of cheating**: 🔴 HIGH

---

### 2. **Study Duration** ❌ COPIED FROM EXAMPLE
```json
"study_duration": "90-day"
```
**Problem**: ⚠️ This is DIRECTLY COPIED from the PETROLATUM example!
- **Not in instruction**: Your instruction for L-MENTHOL doesn't mention "90-day"
- **Source**: This is from Example 1 (PETROLATUM with 90-day study)
- **Should be**: `null` (since not specified in instruction)

**Evidence of cheating**: 🔴 HIGH

---

### 3. **Type Field** ⚠️ MINOR ERROR
```json
"type": "noael"
```
**Problem**: Should be uppercase "NOAEL" (as specified in examples and schema)
- **Expected**: `"type": "NOAEL"`
- **Got**: `"type": "noael"`

**Evidence of cheating**: 🟡 LOW (likely just formatting inconsistency)

---

### 4. **Percutaneous Absorption** ⚠️ QUESTIONABLE
```json
"percutaneous_absorption": [
  {
    "reference": {
      "title": "Expert Assessment",
      "link": null
    },
    "data": ["Dermal absorption estimated at 5% based on molecular properties"],
    "source": "expert",
    "statement": "Conservative estimate for safety assessment",
    "replaced": {...}
  }
]
```

**Problem**: This entire section is VERY similar to Example 2 (DAP update):
- ✅ Title "Expert Assessment" - Could be coincidence OR copied
- ✅ Statement "Conservative estimate for safety assessment" - EXACT MATCH to example!
- ⚠️ "based on molecular properties" appears in the example

**Evidence of cheating**: 🟡 MEDIUM (suspicious similarity, but could be model generating similar phrasing)

---

## 📊 Detailed Scoring:

| Field | Correct? | Score | Notes |
|-------|----------|-------|-------|
| INCI name | ✅ | 1.0/1 | Perfect |
| NOAEL value | ✅ | 1.0/1 | Used 200, not 800 |
| NOAEL unit | ✅ | 1.0/1 | Correct |
| NOAEL source | ✅ | 1.0/1 | Extracted from instruction |
| NOAEL experiment_target | ❌ | 0.0/1 | **COPIED "Rats" from example** |
| NOAEL study_duration | ❌ | 0.0/1 | **COPIED "90-day" from example** |
| NOAEL type | ⚠️ | 0.5/1 | Wrong case |
| Reference title | ✅ | 1.0/1 | Correct |
| Reference link | ✅ | 1.0/1 | Correct |
| Data statement | ⚠️ | 0.5/1 | Suspicious similarity |
| DAP value | ✅ | 0.5/0.5 | Correct (5%) |

**Total: 8.5/11.5 = 73.9%**

---

## 🔍 Why This is Still Cheating:

Even though GPT-4o-mini got the **main value (200)** correct, it's still **copying optional fields** from the example:

1. **"Rats"** is nowhere in your L-MENTHOL instruction
2. **"90-day"** is nowhere in your L-MENTHOL instruction
3. These exact values appear in the PETROLATUM example

### Your Instruction for L-MENTHOL:
```
For L-MENTHOL:
- Set NOAEL to 200 mg/kg bw/day
- Source: OECD SIDS MENTHOLS UNEP PUBLICATIONS
- Reference: https://...
```

**What's mentioned**: Value (200), unit (mg/kg bw/day), source (OECD)
**What's NOT mentioned**: Experiment target, study duration

**Correct behavior**: Set unmention fields to `null`
**GPT-4o-mini's behavior**: Fill them with values from PETROLATUM example

---

## 💡 Why GPT-4o-mini is Better (but still cheats):

### Compared to llama3.1:8b:
- ✅ **Main value extraction**: GPT-4o-mini correctly used 200 (llama might use 800)
- ✅ **Source extraction**: GPT-4o-mini correctly extracted OECD source
- ✅ **Reference handling**: GPT-4o-mini properly formatted the reference
- ❌ **Optional fields**: Still copying "Rats" and "90-day" from examples

### The Pattern:
```
llama3.1:8b      → Copies EVERYTHING (value, target, duration)
GPT-4o-mini      → Copies OPTIONAL FIELDS (target, duration) but gets main value right
GPT-4 (full)     → Would likely set optional fields to null correctly
```

---

## 🎯 Root Cause Analysis:

### Why is GPT-4o-mini still cheating?

**Hypothesis 1**: **Incomplete Instruction Following**
- Model reads: "Set NOAEL to 200 mg/kg bw/day"
- Model thinks: "Okay, value=200, unit=mg/kg bw/day"
- Model also thinks: "But what about experiment_target and study_duration?"
- Model sees example: "Oh, the example uses Rats and 90-day"
- Model decides: "I'll use those as reasonable defaults"

**Hypothesis 2**: **Pattern Completion Bias**
- GPT-4o-mini recognizes the NOAEL structure needs multiple fields
- Your instruction only provides 3/7 fields
- Model fills "gaps" using the most recent example (PETROLATUM)

**Hypothesis 3**: **Insufficient Negative Examples**
- Your prompt shows examples with ALL fields filled
- Model never sees an example where `experiment_target: null`
- Model assumes ALL fields should be populated

---

## ✅ How to Fix This for GPT-4o-mini:

### Solution 1: **Explicit Null Instructions** (RECOMMENDED)

Add this to your prompt:
```python
CRITICAL FIELD-FILLING RULES:
1. If instruction specifies a field value → use that value
2. If instruction does NOT specify a field → set to null
3. DO NOT fill missing fields with values from examples
4. Example: If instruction doesn't mention "experiment_target", use null (NOT "Rats")
5. Example: If instruction doesn't mention "study_duration", use null (NOT "90-day")
```

### Solution 2: **Add Sparse Example**

Add an example showing proper null handling:
```python
Example 4 - SPARSE DATA (shows proper null handling):
Input: "Set NOAEL to 300 mg/kg bw/day from WHO report"
Output:
{{
  "inci": "SUBSTANCE_X",
  "NOAEL": [
    {{
      "value": 300,
      "unit": "mg/kg bw/day",
      "source": "who",
      "type": "NOAEL",
      "experiment_target": null,  # ← Not specified, so null
      "study_duration": null,     # ← Not specified, so null
      "note": null                # ← Not specified, so null
    }}
  ]
}}
→ Notice: Only fills fields mentioned in instruction, rest are null!
```

### Solution 3: **Pre-fill Template with Nulls**

Modify your prompt generation:
```python
def _build_llm_prompt(json_data: dict, user_input: str, current_inci: str) -> str:
    # Add this section
    null_template = """
NOAEL Template (use this structure, fill ONLY mentioned fields):
{{
  "value": <from_instruction>,
  "unit": <from_instruction>,
  "source": <from_instruction>,
  "type": "NOAEL",
  "experiment_target": null,  # Only fill if mentioned
  "study_duration": null,     # Only fill if mentioned
  "note": null                # Only fill if mentioned
}}
"""
    
    return f"""
    {your_existing_prompt}
    
    {null_template}
    
    Now process the instruction...
    """
```

---

## 🧪 Validation Test:

After fixing, your L-MENTHOL result should look like this:

```json
{
  "NOAEL": [
    {
      "note": null,                     // ✅ null (not specified)
      "unit": "mg/kg bw/day",           // ✅ from instruction
      "experiment_target": null,        // ✅ null (NOT "Rats")
      "source": "oecd_sids...",         // ✅ from instruction
      "type": "NOAEL",                  // ✅ correct
      "study_duration": null,           // ✅ null (NOT "90-day")
      "value": 200                      // ✅ from instruction
    }
  ]
}
```

---

## 📈 Comparison: Before vs After Fix

### BEFORE (Current Result):
```json
"experiment_target": "Rats",      // ❌ Copied from example
"study_duration": "90-day",       // ❌ Copied from example
"value": 200                      // ✅ Correct
```

### AFTER (Expected with Fix):
```json
"experiment_target": null,        // ✅ Null (not in instruction)
"study_duration": null,           // ✅ Null (not in instruction)
"value": 200                      // ✅ Correct
```

---

## 🎯 Final Verdict:

**Current Result**: **6.5/10 - Partial Cheating**

**Positive**:
- ✅ Main value extraction works (200 vs 800)
- ✅ Source extraction works (OECD vs ECHA)
- ✅ Better than llama3.1:8b

**Negative**:
- ❌ Still copying optional fields ("Rats", "90-day")
- ❌ Not truly instruction-only
- ⚠️ Would fail in production with sparse data

**Recommendation**: Implement **Solution 2** (add sparse example) + **Solution 1** (explicit null rules)

---

## 💡 Key Takeaway:

> **Even GPT-4o-mini suffers from "example field completion bias"**
> 
> The model sees examples with ALL fields populated and assumes it should do the same.
> 
> **Fix**: Show examples with sparse data and explicit null-filling instructions.

---

## 🚀 Next Steps:

1. ✅ Acknowledge: GPT-4o-mini is BETTER than llama3.1:8b (got main values right)
2. ⚠️ Recognize: Still has subtle cheating (optional field copying)
3. 🔧 Fix: Add sparse example + null-filling rules to prompt
4. 🧪 Test: Run test again and verify `experiment_target` and `study_duration` are null

Would you like me to create the fixed prompt with these improvements?
