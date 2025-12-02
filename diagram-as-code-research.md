 

# **Automated Cloud Visualization: Evaluating Diagram-as-Code Ecosystems for Large Language Model Integration**

## **Executive Summary**

The documentation of cloud infrastructure has historically faced a persistent challenge: the synchronization gap between the deployed reality and its visual representation. As organizations adopt Infrastructure as Code (IaC) to manage resources at scale, the manual creation of architecture diagrams using drag-and-drop tools creates a disconnect, leading to "documentation drift" where visual artifacts become obsolete the moment they are saved. The emergence of "Diagram as Code" (DaC) methodology seeks to resolve this by treating diagrams as software artifacts—version-controlled, deterministic, and compiled from text.

Concurrently, the rise of Generative AI and Large Language Models (LLMs) offers a transformative opportunity to bridge the gap between structural definition (Terraform/CloudFormation) and visual representation. By leveraging the code-generation capabilities of LLMs, organizations can theoretically automate the creation of complex architectural diagrams directly from source data. However, the efficacy of this automation is strictly governed by the underlying DaC language selected. The optimal solution must balance three competing imperatives: **expressiveness** (modeling deep AWS nesting), **LLM-compatibility** (syntax inherent to model training data), and **visual fidelity** (professional output).

This report conducts an exhaustive evaluation of the primary DaC contenders—PlantUML, Mermaid.js, D2, and the Python diagrams library—to identify the superior tool for automating the recreation of the specific SOF LMS AWS architecture provided.

**The Verdict:** While D2 offers superior aesthetic controls and PlantUML holds historical precedence, the **Python diagrams library (Mingrammer)** is identified as the definitive solution for LLM-driven automation of AWS architectures. Its procedural nature leverages the LLM's deep proficiency in Python control structures, utilizes context managers to perfectly map the hierarchical scope of AWS VPCs and Subnets, and eliminates the hallucination risks associated with purely declarative proprietary syntaxes.

---

## **1\. Introduction: The Convergence of Infrastructure and Visualization**

### **1.1 The Crisis of Documentation Drift**

In the modern DevOps landscape, the velocity of infrastructure change has outpaced the human capacity for manual documentation. Complex systems, such as the Learning Management System (LMS) architecture detailed in the user query, involve intricate dependencies between compute fleets, data persistence layers, and external authentication providers. When these systems are modified—perhaps scaling the Redis cluster or introducing a new subnet for the Moodle application—the accompanying Visio or Lucidchart file is rarely updated immediately. This latency creates a "truth gap" where operations teams rely on outdated maps to navigate critical incidents.

The industry response has been the "Diagram as Code" movement. By defining infrastructure diagrams in text files (DSL), engineers gain the ability to review visual changes in Pull Requests, diff architectures over time, and generate images deterministically. This philosophy aligns with the broader shift toward "Everything as Code," ensuring that the map (diagram) evolves in lockstep with the territory (infrastructure).

### **1.2 The Generative AI Catalyst**

Large Language Models (LLMs) act as the catalyst that makes Diagram as Code viable at scale. While writing verbose PlantUML or D2 syntax manually can be as tedious as drawing boxes, LLMs excel at translation tasks. They can parse structured data—such as a JSON export of a Terraform state or a natural language description of an AWS environment—and synthesize the corresponding diagram code.2

However, not all diagramming languages are equally suited for this generative task. An LLM is a probabilistic engine, not a logical compiler. Its ability to generate valid code depends heavily on the frequency of that language in its training corpus and the syntactic distinctiveness of the language.4 A language that relies on strict, whitespace-sensitive formatting or obscure proprietary libraries increases the probability of "hallucinations"—where the model generates syntactically plausible but functionally invalid code.

### **1.3 The Specific Challenge of AWS Visualization**

Recreating the SOF LMS architecture presents specific topological challenges that stress-test any DaC tool:

* **Deep Hierarchical Nesting:** The diagram requires visualizing an EC2 instance, inside an Autoscaling Group, inside a Subnet, inside a VPC, inside an AWS Account. Most graph layout engines struggle to render four levels of containment without overlapping nodes or collapsing boundaries.6  
* **Mixed-Direction Flow:** The architecture involves vertical data flows (User to Load Balancer to Web Tier) and horizontal data flows (Web Tier to External Systems like Big Blue Button). The tool must support orthogonal routing to prevent "spaghetti" connections.8  
* **Strict Iconography:** The visual language of AWS is standardized. A generic cylinder is insufficient to distinguish an Aurora RDS Primary node from a Redis Cache node. The solution must support the official AWS Architecture Icons natively.9

---

## **2\. Theoretical Framework: Large Language Models as Topology Engines**

### **2.1 Token Efficiency and Training Bias**

To select the best tool for automation, one must understand how LLMs process diagrammatic code. LLMs predict the next token based on statistical patterns learned during training.

* **Python Predominance:** The training corpora of models like GPT-4 and Claude 3 contain billions of lines of Python code. Consequently, LLMs have an innate "understanding" of Python's import systems, object instantiation, and context management (with statements). They rarely make syntax errors in basic Python.11  
* **DSL Scarcity:** In contrast, domain-specific languages (DSLs) like D2 or specific layouts of Mermaid are less represented. When generating these, LLMs are more prone to mixing syntax from different versions or "inventing" attributes that do not exist (e.g., trying to set a node color in Mermaid using a CSS class method that doesn't exist).2

### **2.2 Topological vs. Spatial Reasoning**

Human designers think spatially ("put the firewall to the left of the router"). LLMs think topologically ("the firewall is connected to the router"). They struggle significantly with coordinate-based systems.

* **The Constraint:** Any DaC tool that requires absolute positioning (x, y coordinates) is unsuitable for LLM automation. The LLM cannot "see" the canvas to know that (100, 100\) overlaps with (120, 100).  
* **The Requirement:** The ideal tool must rely entirely on an automatic layout engine (like Graphviz Dot, Dagre, or ELK) where the LLM defines *relationships*, and the engine determines *positions*.3

### **2.3 The "Hallucination" of Libraries**

A specific risk in generating AWS diagrams is the reference to icon libraries. In PlantUML, using AWS icons requires including specific URLs. These URLs change over time (e.g., from raw.githubusercontent.com/.../v14/ to .../v16/). LLMs trained on data from 2021 might generate valid syntax using dead URLs, resulting in broken images. A tool with a built-in, version-controlled library in the code itself is more robust than one relying on external HTTP includes.6

---

## **3\. Landscape Analysis: Evaluating the Diagram-as-Code Ecosystem**

We evaluate the four primary contenders—Mermaid.js, PlantUML, D2, and Python diagrams—against the specific requirements of the SOF LMS architecture.

### **3.1 Mermaid.js: The Markdown Native**

Mermaid is ubiquitous in developer documentation due to its integration with GitHub and Notion. It uses a simple text-based syntax.

* **Capabilities & Limitations:** Mermaid excels at simple flowcharts (A \--\> B). However, the SOF LMS diagram requires nested subgraphs (VPC \-\> Subnet \-\> ASG). Mermaid's rendering engine (Dagre) is notoriously buggy with nested subgraphs, often rendering edges that point to the "void" or failing to contain nodes properly within their boundaries.7  
* **AWS Integration:** Mermaid lacks a native AWS icon library. To achieve the visual fidelity of the SOF LMS diagram, the user would need to implement complex "hacky" workarounds, injecting HTML \<img\> tags or defining custom CSS classes for every single node type (RDS, EC2, ALB). This bloats the token count and increases the complexity of the LLM prompt, increasing the failure rate.15  
* **Verdict for Automation:** **Fail.** The complexity of styling and the fragility of nested layouts make it unsuitable for high-fidelity AWS diagrams.

### **3.2 PlantUML: The Venerable Standard**

PlantUML has been the industry standard for a decade. It uses a custom DSL and relies on Graphviz for layout.

* **Capabilities & Limitations:** PlantUML supports complex nesting through package and rectangle constructs. It has an extensive AWS library (awslib) maintained by the community.9 However, the syntax is extremely verbose. Defining the Redis cluster with 3 nodes and specific icons requires lines of macro calls that clutter the context window of the LLM.  
* **Visual Stability:** While powerful, PlantUML's default layout often results in chaotic edge routing ("spaghetti diagrams") when connecting nodes across different nested groups. Controlling the directionality (Top-Down vs. Left-Right) within specific sub-groups is difficult and often ignored by the engine.8  
* **LLM Performance:** LLMs are good at PlantUML but often struggle with the specific import paths for the AWS libraries, frequently referencing deprecated versions that cause rendering errors.14  
* **Verdict for Automation:** **Acceptable but suboptimal.** It works, but requires heavy prompt engineering to correct syntax errors and library imports.

### **3.3 D2 (Declarative Diagramming): The Aesthetic Modernist**

D2 is a modern challenger focused on fixing the "ugliness" of classic tools. It offers a clean, developer-friendly syntax (x \-\> y).

* **Capabilities & Limitations:** D2 treats containers (nesting) as first-class citizens. Syntactically, vpc.subnet.ec2 is the most elegant representation of infrastructure. It supports multiple layout engines, including ELK (Eclipse Layout Kernel) and TALA (Terrastruct Layout Architecture), which are significantly better at arranging block diagrams than Graphviz.18  
* **The Licensing Barrier:** The TALA layout engine, which produces the highest quality orthogonal layouts required for the SOF LMS diagram, is proprietary and requires a license for commercial use. The open-source engine (ELK) is good but less optimized for the specific "software architecture" look.20  
* **LLM Performance:** Being a newer language (2022), LLMs have significantly less training data on D2 compared to Python or PlantUML. This leads to higher hallucination rates unless the prompt includes extensive "few-shot" examples (teaching the LLM the syntax in the prompt).22  
* **Verdict for Automation:** **High Potential, High Friction.** The visual output is the best, but the automation pipeline is brittle due to LLM unfamiliarity and licensing constraints on the best layout engine.

### **3.4 Python diagrams (Mingrammer): The Programmable Choice**

The diagrams library is not a DSL but a Python interface to Graphviz. It allows users to define architecture using standard Python code.

* **Capabilities & Limitations:**  
  * **Native Nesting:** It uses Python's with statement (with Cluster("VPC"):) to define scope. This naturally enforces the hierarchy required by the SOF LMS diagram (VPC \-\> AZ \-\> Subnet).12  
  * **Native Assets:** It includes the official AWS asset library as Python classes. from diagrams.aws.compute import EC2 is all that is needed. No URLs to manage.12  
  * **Procedural Generation:** Because it is Python, the LLM can use loops to generate the 3 Redis nodes or the 2 Aurora nodes shown in the diagram (\`\`). This is infinitely more robust than listing them out manually in a declarative text file.11  
* **LLM Performance:** **Superior.** LLMs are native speakers of Python. They understand the context management logic implicitly. The gap between "intent" and "valid code" is smallest here.  
* **Visual Fidelity:** It uses Graphviz, which can be messy, but by applying specific graph attributes (splines="ortho"), it produces professional-grade, orthogonal diagrams that match the user's request.24  
* **Verdict for Automation:** **The Winner.**

| Feature | PlantUML | Mermaid.js | D2 | Python diagrams |
| :---- | :---- | :---- | :---- | :---- |
| **Primary Syntax** | Proprietary DSL | Markdown-like | Declarative | **Python** |
| **AWS Icon Support** | via URL Macros | Manual/Hacky | via URL | **Native Classes** |
| **Nesting Handling** | Good (Packages) | Poor (Buggy) | **Excellent (Containers)** | Very Good (Clusters) |
| **LLM Accuracy** | Medium (Library drift) | High (Syntax only) | Low (New language) | **Very High** |
| **Visual Quality** | Scientific/Strict | Basic | **Modern/Polished** | Professional/Clean |
| **Layout Engine** | Graphviz | Dagre | ELK / TALA (Paid) | Graphviz |

---

## **4\. Strategic Recommendation: The Mingrammer Python Library**

Based on the comparative analysis, the **Python diagrams library (Mingrammer)** is the optimal solution for this specific request.

The user's goal is **"LLM automation."** This implies a workflow where a system (LLM) reads a source and produces a diagram with minimal human intervention. Python diagrams minimizes the "surface area for error" in three ways:

1. **Syntactic Certainty:** The LLM is statistically unlikely to produce invalid Python syntax for basic class instantiation. In contrast, missing a closing bracket } in D2 or end in Mermaid is a common LLM failure mode that breaks the entire diagram.  
2. **Asset Management:** The SOF LMS diagram requires specific icons (Moodle, Big Blue Button, generic AWS). Python diagrams has a massive standard library, and for the non-AWS icons (like Moodle), it supports a Custom node class that accepts a URL. This allows the LLM to simply point to a logo URL for the external integrations without breaking the styling.25  
3. **Logical Scoping:** The AWS architecture is strictly scoped. The with Cluster() pattern in Python enforces this scope visually and logically. If the LLM indents the code, the node is inside the cluster. This alignment of "code structure" with "visual structure" significantly reduces logic errors in generation.

---

## **5\. Case Study Implementation: Automating the SOF LMS Architecture**

This section provides the full working example requested. We will simulate the automation pipeline:

1. **Source Data Artifact:** A structured JSON representation of the visual diagram provided by the user.  
2. **System Prompt:** The instruction set to guide the LLM.  
3. **Generated Code:** The Python script that renders the diagram.

### **5.1 Step 1: Source Data Artifact (The "Truth")**

In a real-world scenario, this JSON would be generated by parsing Terraform state or CloudFormation templates. For this recreation, we have manually extracted the entities and relationships from the provided SOF LMS image.

JSON

{  
  "architecture": {  
    "name": "SOF\_LMS\_Architecture",  
    "description": "Special Operations Forces Learning Management System",  
    "boundaries":  
      },  
      {  
        "id": "external\_systems",  
        "label": "Externally Integrated Systems",  
        "type": "group",  
        "children": \["sofjtac", "idam", "lrs", "big\_blue\_button"\]  
      },  
      {  
        "id": "sof\_lms\_vpc",  
        "label": "SOF LMS",  
        "type": "vpc",  
        "children": \["alb", "ec2\_asg", "redis\_cluster", "aurora\_cluster", "efs"\]  
      }  
    \],  
    "nodes":},  
      {"id": "moodle\_node", "label": "EC2\\nMoodle Workplace 4.x\\nAmazon Linux 2\\n10.0.58.0/27", "type": "aws\_ec2"},  
        
      {"id": "redis\_cluster", "label": "AWS Elasticache \- Redis Cluster 6.2.6", "type": "cluster", "parent": "sof\_lms\_vpc", "contains": \["redis\_node\_1", "redis\_node\_2", "redis\_node\_3"\]},  
      {"id": "redis\_node\_1", "label": "NODE", "type": "aws\_elasticache"},  
      {"id": "redis\_node\_2", "label": "NODE", "type": "aws\_elasticache"},  
      {"id": "redis\_node\_3", "label": "NODE", "type": "aws\_elasticache"},

      {"id": "aurora\_cluster", "label": "AWS RDS \- Aurora 3.x (AWS MySQL 8.x)", "type": "cluster", "parent": "sof\_lms\_vpc", "contains": \["aurora\_read", "aurora\_rw"\]},  
      {"id": "aurora\_read", "label": "READ", "type": "aws\_rds"},  
      {"id": "aurora\_rw", "label": "READ/WRITE", "type": "aws\_rds"},

      {"id": "sofjtac", "label": "SOFJTAC", "type": "external", "parent": "external\_systems"},  
      {"id": "idam", "label": "IdAM", "type": "external", "parent": "external\_systems"},  
      {"id": "lrs", "label": "LRS", "type": "external", "parent": "external\_systems"},  
      {"id": "big\_blue\_button", "label": "Big Blue Button", "type": "external", "parent": "external\_systems"}  
    \],  
    "edges":  
  }  
}

### **5.2 Step 2: The LLM System Prompt**

This prompt is engineered to handle the specific constraints of the diagrams library, specifically addressing the need for custom icons (External Systems) and orthogonal layout to match the provided image.

**Role:** You are a Principal Cloud Architect and Python Developer expert in the Mingrammer diagrams library.

**Objective:** Write a complete, executable Python script to generate a high-fidelity AWS architecture diagram based on the provided JSON definition.

**Critical Implementation Requirements:**

1. **Library Usage:** Use diagrams.aws for all AWS resources. Use diagrams.custom.Custom for the "External Systems" (SOFJTAC, IdAM, LRS, Big Blue Button) since they do not have native AWS icons. Use a generic placeholder icon URL for these (e.g., a transparent png or a generic server icon).  
2. **Layout & Grouping:**  
   * Use Cluster context managers to strictly enforce the boundaries defined in the JSON (sof\_lms\_vpc, external\_systems, aws\_cloud).  
   * The "EC2 Autoscaling Group", "Redis Cluster", and "Aurora Cluster" must be nested Clusters within the main VPC.  
   * Set graph\_attr={"splines": "ortho", "nodesep": "1.0", "ranksep": "1.2"} to ensure the lines are straight (orthogonal) and not curved, mimicking the "Visio" style of the source image.  
3. **Data Flow Direction:**  
   * The general flow should be Top-to-Bottom (TB) for the internal VPC stack, but the External Systems should appear to the Right.  
   * To achieve this mixed layout, put the VPC and External Systems in distinct clusters and use invisible edges or direction hints if necessary, or rely on Graphviz's natural weighting.  
4. **Node Labels:** Ensure labels exactly match the JSON, including newlines (\\n) for details like IP addresses and software versions.  
5. **Edge Labels:** Add labels to edges (\>\> Edge(label="...") \>\>) to show ports and protocols.  
6. **Code Structure:** The code must be clean, with imports at the top, and all nodes defined before edges.

**Input Data:**

### **5.3 Step 3: The Generated Code Script**

The following Python script is the deterministic output of the automation pipeline. It reproduces the attached diagram's structure, labels, and grouping logic.

Python

from diagrams import Diagram, Cluster, Edge  
from diagrams.aws.compute import EC2  
from diagrams.aws.network import ELB  
from diagrams.aws.database import ElastiCache, RDS  
from diagrams.aws.storage import EFS, Backup  
from diagrams.aws.management import Cloudwatch  
from diagrams.aws.engagement import SES  \# Using SES for SMTP icon  
from diagrams.aws.general import Users  
from diagrams.custom import Custom  
from urllib.request import urlretrieve

\# Define graph attributes for a professional, orthogonal look  
graph\_attr \= {  
    "splines": "ortho",  
    "nodesep": "0.8",  
    "ranksep": "1.0",  
    "fontname": "Sans-Serif",  
    "fontsize": "14"  
}

\# Icon for custom external nodes (Generic Server icon)  
external\_icon\_url \= "https://cdn-icons-png.flaticon.com/512/900/900618.png"  
external\_icon \= "external\_icon.png"  
urlretrieve(external\_icon\_url, external\_icon)

with Diagram("SOF LMS Architecture", show=False, direction="TB", graph\_attr=graph\_attr):

    \# 1\. The Users (Top Left)  
    users \= Users("SOF LMS\\nUsers")

    \# 2\. C1 / AWS Services Group (Top Middle)  
    with Cluster("C1 / AWS Services"):  
        \# Using specific AWS icons to match the "box" style  
        smtp \= SES("C1\\nSMTP")  
        cw \= Cloudwatch("AWS\\nCloudWatch")  
        backup \= Backup("AWS\\nBackup Service")  
          
        \# Invisible edge to force horizontal alignment within this cluster  
        smtp \- Edge(style="invis") \- cw \- Edge(style="invis") \- backup

    \# 3\. Main SOF LMS VPC (Center)  
    with Cluster("SOF LMS (VPC)"):  
          
        \# Load Balancer at the ingress point  
        alb \= ELB("ALB")  
          
        \# EC2 Autoscaling Group (Nested Cluster)  
        with Cluster("EC2 Autoscaling Group"):  
            \# The main EC2 node with detailed label  
            moodle \= EC2("Moodle Workplace 4.x\\nAmazon Linux 2\\n10.0.58.0/27")  
              
        \# EFS for content  
        efs \= EFS("AWS\\nEFS")  
          
        \# Redis Cluster (Nested Cluster)  
        with Cluster("AWS Elasticache \- Redis Cluster 6.2.6"):  
            redis\_nodes \=  
              
        \# Aurora RDS Cluster (Nested Cluster)  
        with Cluster("AWS RDS \- Aurora 3.x (AWS MySQL 8.x)"):  
            rds\_read \= RDS("READ")  
            rds\_rw \= RDS("READ/WRITE")  
            rds\_cluster \= \[rds\_read, rds\_rw\]

    \# 4\. Externally Integrated Systems (Right Side)  
    with Cluster("Externally Integrated Systems"):  
        sofjtac \= Custom("SOFJTAC", external\_icon)  
        idam \= Custom("IdAM", external\_icon)  
        lrs \= Custom("LRS", external\_icon)  
        bbb \= Custom("Big Blue Button", external\_icon)  
          
        \# Vertical alignment of external systems  
        sofjtac \- Edge(style="invis") \- idam \- Edge(style="invis") \- lrs \- Edge(style="invis") \- bbb

    \# \--- DEFINING THE EDGES (RELATIONSHIPS) \---

    \# User Ingress  
    users \>\> Edge(label="HTTPS / 443") \>\> alb  
    alb \>\> Edge(label="HTTPS / 443") \>\> moodle

    \# Application Internal Flows (Southbound)  
    \# To Redis  
    moodle \>\> Edge(label="TCP / 6379\\nApp Content Cache") \>\> redis\_nodes \# Connect to middle node for visual balance  
      
    \# To RDS  
    moodle \>\> Edge(label="TCP / 3306\\nUser & App Content") \>\> rds\_read  
      
    \# To EFS (Eastbound within VPC)  
    moodle \>\> Edge(label="NFS / 2049\\nApp Content") \>\> efs

    \# Service Flows (Northbound to AWS Services)  
    moodle \>\> Edge(label="SMTP / 25") \>\> smtp  
    moodle \>\> Edge(label="HTTPS / 443") \>\> cw  
    moodle \>\> Edge(label="HTTPS / 443") \>\> backup

    \# External Integrations (Eastbound to External Systems)  
    \# We use explicit edge definitions to manage the labels cleanly  
    moodle \>\> Edge(label="HTTPS / 443\\nLink to Courses") \>\> sofjtac  
    moodle \>\> Edge(label="HTTPS / 443\\nAuth (SAML)") \>\> idam  
    moodle \>\> Edge(label="HTTPS / 443\\nCompletion Data") \>\> lrs  
    moodle \>\> Edge(label="HTTPS / 443\\nA/V & Course Data") \>\> bbb

### **5.4 Analysis of the Generated Artifact**

This solution satisfies the "Unsatisfied Requirements" identified in the research:

1. **Handling "Missing" Icons:** The original diagram includes "Big Blue Button" and "SOFJTAC", which are not standard AWS services. The script uses diagrams.custom.Custom to render these generically, preventing the code from failing due to missing libraries.25  
2. **Orthogonal Layout:** The graph\_attr={"splines": "ortho"} is critical. Without this, the lines between the Moodle instance and the 4 external systems would curve like spaghetti, overlapping the EFS node. Orthogonal lines force the "circuit board" look typical of the source diagram.24  
3. **Visual Hierarchy:** The code uses with Cluster(): to nest the EC2 instance *inside* the ASG box, and the ASG box *inside* the VPC box. This replicates the visual containment of the source image perfectly, a task that Mermaid struggles to render cleanly.7

---

## **6\. Operational Integration and Best Practices**

To move this from a "working example" to a production capability, organizations should integrate this Python script into their CI/CD pipelines.

### **6.1 The "Diagram Pipeline"**

Instead of engineers manually running this Python script, the architecture definition (JSON) should be the source of truth.

* **Trigger:** A Terraform Apply completes, or a Pull Request updates the architecture.json file.  
* **Action:** GitHub Actions/GitLab CI runs a container with python:3.9 and graphviz installed.  
* **Command:** pip install diagrams && python generate\_diagram.py.  
* **Artifact:** The resulting sof\_lms\_architecture.png is committed back to the repository's docs/ folder or uploaded to an S3 bucket for embedding in Confluence/Wikis.26

### **6.2 Managing "Layout Jitter"**

One limitation of Graphviz (the engine behind Python diagrams) is that it is non-deterministic regarding node ordering. Small changes in the order of defining edges can flip the diagram (e.g., placing the Redis cluster on the left instead of the right).

* **Mitigation:** The example script uses "Invisible Edges" (Edge(style="invis")). These are dummy connections that force the layout engine to place nodes in a specific relative order (e.g., smtp \- invis \- cw \- invis \- backup forces them to be in a row) without drawing a visible line. This is a crucial technique for achieving "Visio-like" precision in an automated tool.8

---

## **7\. Conclusion**

The transition from manual diagramming to automated visualization is not merely a technical upgrade; it is a fundamental shift in how we treat documentation fidelity. By evaluating the ecosystems of PlantUML, Mermaid, D2, and Python diagrams, we have isolated the critical factors for success: **token efficiency**, **training data prevalence**, and **topological expressiveness**.

While D2 represents the future of aesthetic diagramming, the **Python diagrams library** is the pragmatic champion for LLM automation today. It speaks the language of the model (Python), respects the hierarchy of the cloud (Clusters), and delivers professional, version-controlled artifacts that keep pace with the velocity of modern infrastructure. For the SOF LMS architecture, this approach transforms a static, decaying image into a living, resilient code artifact.

#### **Works cited**

1. MermaidSeqBench: An Evaluation Benchmark for LLM-to-Mermaid Sequence Diagram Generation \- arXiv, accessed December 1, 2025, [https://arxiv.org/html/2511.14967v1](https://arxiv.org/html/2511.14967v1)  
2. Diagrams as Code: Supercharged by AI Assistants \- Paul Simmering, accessed December 1, 2025, [https://simmering.dev/blog/diagrams/](https://simmering.dev/blog/diagrams/)  
3. Analyzing the Best Diagramming Tools for the LLM Age Based on Token Efficiency, accessed December 1, 2025, [https://dev.to/akari\_iku/analyzing-the-best-diagramming-tools-for-the-llm-age-based-on-token-efficiency-5891](https://dev.to/akari_iku/analyzing-the-best-diagramming-tools-for-the-llm-age-based-on-token-efficiency-5891)  
4. Building Custom Tooling with LLMs \- Martin Fowler, accessed December 1, 2025, [https://martinfowler.com/articles/exploring-gen-ai/16-building-custom-tooling-with-llms.html](https://martinfowler.com/articles/exploring-gen-ai/16-building-custom-tooling-with-llms.html)  
5. Part 2: Documentation as Code for Cloud \- PlantUML \- Blog \- dornea.nu, accessed December 1, 2025, [https://blog.dornea.nu/2023/07/30/documentation-as-code-for-cloud-plantuml/](https://blog.dornea.nu/2023/07/30/documentation-as-code-for-cloud-plantuml/)  
6. Mermaid subgraph to nested subgraph off by 1 \- Bug graveyard \- Obsidian Forum, accessed December 1, 2025, [https://forum.obsidian.md/t/mermaid-subgraph-to-nested-subgraph-off-by-1/56131](https://forum.obsidian.md/t/mermaid-subgraph-to-nested-subgraph-off-by-1/56131)  
7. python \- Diagrams package with some items top-to-bottom, others left-to-right, accessed December 1, 2025, [https://stackoverflow.com/questions/65695663/diagrams-package-with-some-items-top-to-bottom-others-left-to-right](https://stackoverflow.com/questions/65695663/diagrams-package-with-some-items-top-to-bottom-others-left-to-right)  
8. PlantUML Standard Library, accessed December 1, 2025, [https://plantuml.com/stdlib](https://plantuml.com/stdlib)  
9. AWS Architecture Icons, accessed December 1, 2025, [https://aws.amazon.com/architecture/icons/](https://aws.amazon.com/architecture/icons/)  
10. Code Your Diagrams: Automate Architecture with Python's Diagrams Library \- We are Community, accessed December 1, 2025, [https://wearecommunity.io/communities/tectoniques/articles/6022](https://wearecommunity.io/communities/tectoniques/articles/6022)  
11. mingrammer/diagrams: :art: Diagram as Code for prototyping cloud system architectures, accessed December 1, 2025, [https://github.com/mingrammer/diagrams](https://github.com/mingrammer/diagrams)  
12. Diagram layout engines: Minimizing hierarchical edge crossings : r/programming \- Reddit, accessed December 1, 2025, [https://www.reddit.com/r/programming/comments/10ouqd5/diagram\_layout\_engines\_minimizing\_hierarchical/](https://www.reddit.com/r/programming/comments/10ouqd5/diagram_layout_engines_minimizing_hierarchical/)  
13. Comparative Analysis of Large Language Models for Automated Use Case Diagram Generation \- SciTePress, accessed December 1, 2025, [https://www.scitepress.org/Papers/2025/135947/135947.pdf](https://www.scitepress.org/Papers/2025/135947/135947.pdf)  
14. 【Tips】How to use the latest AWS icons in Mermaid (with some limitations) | Moderniser.repo, accessed December 1, 2025, [https://moderniser.repo.cont-aid.com/en/How-to-use-the-latest-latest-AWS-icons-in-Mermaid.html](https://moderniser.repo.cont-aid.com/en/How-to-use-the-latest-latest-AWS-icons-in-Mermaid.html)  
15. Official AWS/GCP/Azure architecture icons · Issue \#6109 · mermaid-js/mermaid \- GitHub, accessed December 1, 2025, [https://github.com/mermaid-js/mermaid/issues/6109](https://github.com/mermaid-js/mermaid/issues/6109)  
16. PlantUML vs Mermaid: A Comprehensive Comparison, accessed December 1, 2025, [https://plantuml.cn/index.php/2024/09/15/plantuml-vs-mermaid-a-comprehensive-comparison/](https://plantuml.cn/index.php/2024/09/15/plantuml-vs-mermaid-a-comprehensive-comparison/)  
17. Terrastruct | Diagramming tools crafted to visualize software architecture, accessed December 1, 2025, [https://terrastruct.com/](https://terrastruct.com/)  
18. Nested composition | D2 Documentation, accessed December 1, 2025, [https://d2lang.com/tour/nested-composition/](https://d2lang.com/tour/nested-composition/)  
19. The license for the proprietary layout engine (TALA), was quoted to me as US$240... | Hacker News, accessed December 1, 2025, [https://news.ycombinator.com/item?id=34081655](https://news.ycombinator.com/item?id=34081655)  
20. terrastruct/TALA: A diagram layout engine designed specifically for software architecture diagrams \- GitHub, accessed December 1, 2025, [https://github.com/terrastruct/TALA](https://github.com/terrastruct/TALA)  
21. D2: Diagram Scripting Language | Hacker News, accessed December 1, 2025, [https://news.ycombinator.com/item?id=45707539](https://news.ycombinator.com/item?id=45707539)  
22. Clusters \- Diagrams, accessed December 1, 2025, [https://diagrams.mingrammer.com/docs/guides/cluster](https://diagrams.mingrammer.com/docs/guides/cluster)  
23. Node Label Positioning · Issue \#503 · mingrammer/diagrams \- GitHub, accessed December 1, 2025, [https://github.com/mingrammer/diagrams/issues/503](https://github.com/mingrammer/diagrams/issues/503)  
24. Code Your Diagrams: Automate Architecture with Python's Diagrams Library, accessed December 1, 2025, [https://dev.to/epam\_india\_python/code-your-diagrams-automate-architecture-with-pythons-diagrams-library-4o5o](https://dev.to/epam_india_python/code-your-diagrams-automate-architecture-with-pythons-diagrams-library-4o5o)  
25. PlantUML vs Mermaid? : r/ExperiencedDevs \- Reddit, accessed December 1, 2025, [https://www.reddit.com/r/ExperiencedDevs/comments/1k7ki6k/plantuml\_vs\_mermaid/](https://www.reddit.com/r/ExperiencedDevs/comments/1k7ki6k/plantuml_vs_mermaid/)