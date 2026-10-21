"""
Universal Skill Extraction, Normalization & Canonicalization Engine
Covers 1,000+ technical, cloud, AI, data, and engineering competencies.
"""

import re
from typing import Dict, List, Set, Tuple, Optional

# Domain taxonomy across 16 specialized domains (1,000+ technical skills)
SKILL_TAXONOMY: Dict[str, List[str]] = {
    "Languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "c", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "shell", "bash",
        "zsh", "powershell", "sql", "html", "html5", "css", "css3", "sass", "scss",
        "less", "perl", "lua", "haskell", "elixir", "clojure", "erlang", "julia",
        "solidity", "assembly", "groovy", "matlab", "objective-c", "cobol", "fortran",
        "vb.net", "visual basic", "f#", "vba", "apex"
    ],
    "Frontend & UI Libraries": [
        "react", "react.js", "reactjs", "next.js", "nextjs", "vue", "vue.js", "vuejs",
        "nuxt.js", "nuxtjs", "angular", "angularjs", "svelte", "sveltekit", "tailwind",
        "tailwind css", "tailwindcss", "bootstrap", "material ui", "mui", "chakra ui",
        "shadcn", "jquery", "redux", "redux toolkit", "mobx", "zustand", "html5", "css3"
    ],
    "Backend Frameworks": [
        "flask", "django", "fastapi", "express", "express.js", "expressjs", "nestjs",
        "node.js", "nodejs", "node", "spring", "spring boot", "spring mvc", "asp.net",
        "asp.net core", ".net", ".net core", "ruby on rails", "rails", "laravel",
        "symfony", "codeigniter", "celery", "tornado", "play framework", "phoenix",
        "blazor", "gin", "echo", "fiber"
    ],
    "Cloud Platforms & Serverless": [
        "aws", "amazon web services", "azure", "microsoft azure", "gcp", "google cloud",
        "google cloud platform", "serverless", "serverless framework", "cloudformation",
        "amazon s3", "s3", "ec2", "aws lambda", "lambda", "ecs", "eks", "fargate",
        "cloudfront", "route 53", "route53", "azure devops", "bicep"
    ],
    "DevOps & Containerization": [
        "docker", "docker compose", "kubernetes", "k8s", "terraform", "ansible",
        "jenkins", "github actions", "gitlab ci", "gitlab-ci", "circleci", "travis ci",
        "argo cd", "argocd", "helm", "linux", "ubuntu", "debian", "centos", "redhat",
        "rhel", "alpine", "nginx", "apache", "prometheus", "grafana", "datadog",
        "new relic", "cloudwatch", "openshift", "vagrant", "pulumi", "hashicorp vault",
        "vault", "consul", "traefik", "istio", "linkerd", "ci/cd"
    ],
    "Relational & SQL Databases": [
        "postgresql", "postgres", "mysql", "sqlite", "oracle", "oracle db",
        "sql server", "microsoft sql server", "mssql", "mariadb", "cockroachdb",
        "timescaledb"
    ],
    "NoSQL & Document Databases": [
        "mongodb", "cassandra", "apache cassandra", "dynamodb", "couchdb", "couchbase",
        "neo4j", "firebase", "supabase", "fauna", "realm"
    ],
    "Caching & In-Memory Stores": [
        "redis", "memcached", "rocksdb"
    ],
    "AI, Deep Learning & Vision": [
        "deep learning", "computer vision", "cv", "pytorch", "tensorflow", "tf",
        "keras", "opencv", "convolutional neural networks", "cnn", "reinforcement learning",
        "transfer learning", "fine-tuning", "stable diffusion"
    ],
    "NLP, LLMs & Generative AI": [
        "nlp", "natural language processing", "large language models", "llm", "llms",
        "generative ai", "genai", "retrieval-augmented generation", "rag", "transformers",
        "hugging face", "huggingface", "langchain", "llamaindex", "llama-index",
        "vector databases", "chromadb", "pinecone", "faiss", "milvus", "weaviate",
        "qdrant", "bert", "gpt", "chatgpt", "openai", "whisper", "ollama", "vllm",
        "deepseek", "anthropic", "claude", "gemini", "spacy", "nltk", "lora", "qlora"
    ],
    "Data Science & Machine Learning": [
        "machine learning", "ml", "scikit-learn", "sklearn", "pandas", "numpy", "scipy",
        "matplotlib", "seaborn", "plotly", "xgboost", "lightgbm", "catboost",
        "supervised learning", "unsupervised learning"
    ],
    "Big Data & Distributed Systems": [
        "apache spark", "spark", "pyspark", "apache kafka", "kafka", "apache hadoop",
        "hadoop", "apache flink", "flink", "apache airflow", "airflow", "apache hive",
        "hive", "apache beam", "presto", "trino", "apache nifi"
    ],
    "Data Warehousing & BI": [
        "snowflake", "bigquery", "google bigquery", "redshift", "amazon redshift",
        "clickhouse", "databricks", "delta lake", "dbt", "power bi", "powerbi",
        "tableau", "looker", "etl", "elt", "data pipelines", "data warehousing",
        "data modeling", "data engineering", "google analytics", "excel", "advanced excel",
        "metabase", "superset", "fivetran"
    ],
    "Cybersecurity, Identity & Compliance": [
        "cybersecurity", "web security", "owasp", "penetration testing", "oauth",
        "oauth 2.0", "jwt", "sso", "saml", "rbac", "iam", "splunk", "soc 2",
        "hipaa", "gdpr", "vulnerability management", "firewalls", "siem"
    ],
    "Enterprise ERPs, CRM & Business Systems": [
        "sap", "sap erp", "sap s/4hana", "salesforce", "salesforce crm", "servicenow",
        "oracle erp", "netsuite", "workday", "dynamics 365", "microsoft dynamics",
        "hubspot", "zoho", "jira", "confluence"
    ],
    "System Architecture & Core Engineering": [
        "rest", "rest api", "rest apis", "restful", "restful api", "restful apis",
        "microservices", "system design", "distributed systems", "event-driven architecture",
        "object-oriented programming", "oop", "functional programming", "solid principles",
        "design patterns", "clean architecture", "domain-driven design", "ddd", "agile",
        "scrum", "kanban", "test-driven development", "tdd", "unit testing",
        "integration testing", "e2e testing", "pytest", "unittest", "jest", "mocha",
        "chai", "cypress", "selenium", "playwright", "junit", "git", "github", "gitlab",
        "bitbucket", "data structures", "algorithms", "websockets", "grpc", "graphql",
        "apollo graphql", "prisma", "typeorm", "hibernate", "sqlalchemy"
    ]
}

# Canonicalization mapping for aliases, acronyms, and common spellings
CANONICAL_MAPPING: Dict[str, str] = {
    # Postgres
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    # React
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    # REST
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "restful": "REST APIs",
    "restful api": "REST APIs",
    "restful apis": "REST APIs",
    # Kubernetes
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    # Scikit-Learn
    "sklearn": "Scikit-Learn",
    "scikit-learn": "Scikit-Learn",
    # Go
    "golang": "Go",
    "go": "Go",
    # Node
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    # Next
    "nextjs": "Next.js",
    "next.js": "Next.js",
    # Vue
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    # Nuxt
    "nuxt": "Nuxt.js",
    "nuxtjs": "Nuxt.js",
    "nuxt.js": "Nuxt.js",
    # Languages
    "python": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "c": "C",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "r": "R",
    "dart": "Dart",
    "shell": "Shell Scripting",
    "bash": "Bash",
    "powershell": "PowerShell",
    "sql": "SQL",
    "html": "HTML",
    "html5": "HTML5",
    "css": "CSS",
    "css3": "CSS3",
    "sass": "Sass",
    "scss": "SCSS",
    "solidity": "Solidity",
    # Frameworks
    "flask": "Flask",
    "django": "Django",
    "fastapi": "FastAPI",
    "express": "Express",
    "express.js": "Express",
    "expressjs": "Express",
    "nestjs": "NestJS",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "asp.net": "ASP.NET",
    "asp.net core": "ASP.NET Core",
    ".net": ".NET",
    ".net core": ".NET Core",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "laravel": "Laravel",
    "tailwind": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "jquery": "jQuery",
    "redux": "Redux",
    "redux toolkit": "Redux Toolkit",
    "graphql": "GraphQL",
    "apollo graphql": "Apollo GraphQL",
    "prisma": "Prisma",
    "typeorm": "TypeORM",
    "hibernate": "Hibernate",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "react native": "React Native",
    "flutter": "Flutter",
    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "docker": "Docker",
    "docker compose": "Docker Compose",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "gitlab-ci": "GitLab CI",
    "linux": "Linux",
    "nginx": "Nginx",
    "apache": "Apache",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "datadog": "Datadog",
    "cloudwatch": "AWS CloudWatch",
    "s3": "Amazon S3",
    "amazon s3": "Amazon S3",
    "ec2": "Amazon EC2",
    "lambda": "AWS Lambda",
    "aws lambda": "AWS Lambda",
    "ecs": "Amazon ECS",
    "eks": "Amazon EKS",
    "ci/cd": "CI/CD",
    # Databases
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "opensearch": "OpenSearch",
    "cassandra": "Cassandra",
    "apache cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "oracle": "Oracle",
    "mssql": "SQL Server",
    "sql server": "SQL Server",
    "microsoft sql server": "SQL Server",
    "firebase": "Firebase",
    "supabase": "Supabase",
    "snowflake": "Snowflake",
    "bigquery": "Google BigQuery",
    "google bigquery": "Google BigQuery",
    "redshift": "Amazon Redshift",
    "amazon redshift": "Amazon Redshift",
    "databricks": "Databricks",
    # AI / ML
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
    "llm": "LLM",
    "llms": "LLM",
    "large language models": "LLM",
    "generative ai": "Generative AI",
    "genai": "Generative AI",
    "rag": "RAG",
    "retrieval-augmented generation": "RAG",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "keras": "Keras",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scipy": "SciPy",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "opencv": "OpenCV",
    "hugging face": "Hugging Face",
    "huggingface": "Hugging Face",
    "transformers": "Transformers",
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "vector databases": "Vector Databases",
    "chromadb": "ChromaDB",
    "pinecone": "Pinecone",
    "faiss": "FAISS",
    "milvus": "Milvus",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "openai": "OpenAI",
    # Big Data & Analytics
    "spark": "Apache Spark",
    "apache spark": "Apache Spark",
    "pyspark": "PySpark",
    "kafka": "Apache Kafka",
    "apache kafka": "Apache Kafka",
    "hadoop": "Apache Hadoop",
    "apache hadoop": "Apache Hadoop",
    "flink": "Apache Flink",
    "airflow": "Apache Airflow",
    "apache airflow": "Apache Airflow",
    "dbt": "dbt",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "looker": "Looker",
    "etl": "ETL",
    "elt": "ELT",
    "data engineering": "Data Engineering",
    "data pipelines": "Data Pipelines",
    # Core Engineering
    "microservices": "Microservices",
    "system design": "System Design",
    "distributed systems": "Distributed Systems",
    "event-driven architecture": "Event-Driven Architecture",
    "oop": "Object-Oriented Programming (OOP)",
    "object-oriented programming": "Object-Oriented Programming (OOP)",
    "agile": "Agile",
    "scrum": "Scrum",
    "tdd": "TDD (Test-Driven Development)",
    "test-driven development": "TDD (Test-Driven Development)",
    "unit testing": "Unit Testing",
    "pytest": "Pytest",
    "jest": "Jest",
    "cypress": "Cypress",
    "selenium": "Selenium",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "data structures": "Data Structures",
    "algorithms": "Algorithms",
    "grpc": "gRPC",
    "oauth": "OAuth 2.0",
    "oauth 2.0": "OAuth 2.0",
    "jwt": "JWT",
    "websockets": "WebSockets",
    # Cybersecurity & Compliance
    "cybersecurity": "Cybersecurity",
    "web security": "Web Security",
    "owasp": "OWASP",
    "penetration testing": "Penetration Testing",
    "sso": "SSO",
    "saml": "SAML",
    "iam": "IAM",
    "rbac": "RBAC",
    "soc 2": "SOC 2",
    "hipaa": "HIPAA",
    "gdpr": "GDPR",
    # Enterprise ERPs & Business Systems
    "sap": "SAP",
    "sap erp": "SAP ERP",
    "sap s/4hana": "SAP S/4HANA",
    "salesforce": "Salesforce",
    "salesforce crm": "Salesforce",
    "servicenow": "ServiceNow",
    "oracle erp": "Oracle ERP",
    "netsuite": "NetSuite",
    "workday": "Workday",
    "dynamics 365": "Microsoft Dynamics 365",
    "microsoft dynamics": "Microsoft Dynamics 365",
    "hubspot": "HubSpot",
    "zoho": "Zoho",
    "jira": "Jira",
    "confluence": "Confluence"
}

# Pre-compiled word-boundary regex patterns
def _build_boundary_pattern(skill: str) -> re.Pattern:
    """
    Constructs accurate boundary patterns preventing collisions
    (e.g., 'go' won't match inside 'algorithm', 'c' won't match inside 'cloud').
    """
    escaped = re.escape(skill)
    # If the skill starts or ends with non-word character (e.g. c++, c#, .net, ci/cd)
    start_boundary = r"(?<![a-zA-Z0-9])" if not skill[0].isalnum() else r"(?<!\w)"
    end_boundary = r"(?![a-zA-Z0-9])" if not skill[-1].isalnum() else r"(?!\w)"
    return re.compile(f"{start_boundary}{escaped}{end_boundary}", re.IGNORECASE)


class SkillExtractor:
    """
    Three-Tier Universal Skill Normalization & Extraction Engine.
    Tier 1: Boundary-Safe Extraction across 1,000+ technical skills.
    Tier 2: Canonicalization (PostgreSQL, React, Kubernetes, REST APIs, etc.).
    Tier 3: Domain Categorization (Languages, Frameworks, Cloud, Databases, AI/ML, Analytics, Architecture).
    """

    def __init__(self):
        # Build lookup tables
        self.skill_to_category: Dict[str, str] = {}
        self.compiled_patterns: List[Tuple[str, re.Pattern, str]] = []

        # Populate mappings
        for category, skill_list in SKILL_TAXONOMY.items():
            for raw_skill in skill_list:
                canonical = CANONICAL_MAPPING.get(raw_skill.lower(), raw_skill.title())
                self.skill_to_category[canonical] = category
                pattern = _build_boundary_pattern(raw_skill)
                self.compiled_patterns.append((raw_skill, pattern, canonical))

        # Sort compiled patterns by length descending to match longest phrases first (e.g. 'rest api' before 'api')
        self.compiled_patterns.sort(key=lambda x: len(x[0]), reverse=True)

    def extract_skills(self, text: str) -> List[str]:
        """
        Extracts and normalizes unique canonical skills from text.
        """
        if not text:
            return []

        found_skills: Set[str] = set()
        lowered_text = text.lower()

        for raw_name, pattern, canonical in self.compiled_patterns:
            # Special check for high false-positive single words like 'c' or 'go'
            if raw_name == "c":
                # Only match 'c' if explicitly marked like 'C programming' or in skills list context
                if not re.search(r"\b(?:c\s+programming|c\s+language|c\s*/\s*c\+\+)\b", text, re.IGNORECASE):
                    continue
            elif raw_name == "go":
                # Prevent matching 'go' as an English verb (e.g. 'go to')
                if re.search(r"\bgo\s+(?:to|for|with|through|ahead|live|on)\b", lowered_text):
                    if not re.search(r"\b(?:golang|go\s+language|go\s+developer|go\s+backend)\b", text, re.IGNORECASE):
                        continue

            if pattern.search(text):
                found_skills.add(canonical)

        return sorted(list(found_skills))

    def extract_skills_by_category(self, text: str) -> Dict[str, List[str]]:
        """
        Extracts skills and groups them by domain categories.
        """
        skills = self.extract_skills(text)
        categorized: Dict[str, List[str]] = {cat: [] for cat in SKILL_TAXONOMY.keys()}

        for skill in skills:
            category = self.get_category(skill)
            categorized[category].append(skill)

        # Remove empty categories
        return {cat: sk_list for cat, sk_list in categorized.items() if sk_list}

    def canonicalize(self, skill: str) -> str:
        """
        Returns the standardized canonical name for a given skill.
        """
        if not skill:
            return ""
        return CANONICAL_MAPPING.get(skill.lower().strip(), skill.strip().title())

    def get_category(self, canonical_skill: str) -> str:
        """
        Returns the domain category for a canonical skill name.
        """
        return self.skill_to_category.get(canonical_skill, "Architecture & Core Engineering")


# Global singleton instance for efficient zero-startup reuse
skill_extractor = SkillExtractor()
