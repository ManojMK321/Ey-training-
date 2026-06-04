**MSF (Medecins Sans Frontieres)**





**1. What to use: ETL or ELT?**

&#x20;**Chosen approach: ETL (Extract → Transform → Load)**



**2. Why do we use it?**

**We use ETL here mainly because:**



**Sensitive patient data must be anonymized BEFORE storage**

**Raw CSVs from 400 sites are inconsistent → need standardization early**

**No need for real-time → allows preprocessing**

**Ensures clean, safe, unified data enters BigQuery**



**In short:**



**ETL ensures data privacy + data quality BEFORE data reaches the central system**





**3. Key Dimensions to Weigh (Decision Factors)**

**From your images, here are the important dimensions and how they influence the decision:**



**🔹 1. Data Sensitivity (Critical)**



**Patient data includes:**

**Names**

**Diagnoses**

**GPS locations**



**⚠️ Risk: Exposure could endanger lives**

**✅ Decision:**

**Must anonymize BEFORE storage**

**→ ETL strongly preferred**





**🔹 2. Infrastructure Constraints**



**Data arrives as daily batch CSV uploads**

**No real-time streaming**

**BigQuery is the destination**



**✅ Decision:**



**Batch-friendly workload → ETL is suitable**

**No need for ELT’s streaming flexibility**





**🔹 3. Data Format Variability**



**400 sites → different schemas:**



**Column names vary**

**Date formats differ**

**Languages differ**



**✅ Decision:**



**Requires heavy preprocessing \& normalization**

**→ Better handled in ETL before loading**





**🔹 4. Analytics Requirements**



**Ad-hoc queries**

**Evolving requirements (no fixed schema)**



**Observation:**



**ELT is better for flexibility**

**BUT only after clean data exists**



**✅ Decision compromise:**



**Use ETL to clean → then flexible analytics in warehouse**





**🔹 5. Latency Tolerance**



**24-hour delay is acceptable**

**No real-time requirement**



**✅ Decision:**



**ETL batch pipelines fit perfectly**





**🔹 6. Cost / Compute Consideration**



**ETL shifts compute outside warehouse**

**Avoids heavy transformation inside BigQuery**



**✅ Decision:**



**Efficient and controlled processing**







**4. Comparison Applied to This Case**





|Dimension|ELT (Not Ideal)|ETL (Chosen ✅)|
|-|-|-|
|Data sensitivity|Raw data stored → risky|Safe → anonymized before load ✅|
|Raw data handling|Stores raw inconsistent data|Clean standardized data ✅|
|Transformation stage|Happens after loading|Happens before loading ✅|
|Latency|Works, but not required advantage|Perfect for batch ✅|
|High|High|Moderate|
|Lower pipelines|Lower pipelines|Slightly higher but necessary ✅|







**5. Final Justification (Very Important)**

**Why NOT ELT?**



**ELT would load raw sensitive data into BigQuery**

**Violates data protection requirements**

**Leads to security risks and compliance issues**





**Why ETL is best here:**



**Ensures full anonymization BEFORE storage**

**Handles data inconsistency across 400 sites**

**Matches batch upload nature**

**Meets low-latency requirement (24-hour acceptable)**

**Protects patients and field staff**



**✅Final Verdict**

&#x09;**Choose: ETL Architecture**

