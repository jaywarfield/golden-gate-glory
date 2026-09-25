from ibmdiagrams.ibmcloud.diagram import *
from ibmdiagrams.ibmcloud.ai import *
from ibmdiagrams.ibmcloud.actors import *
from ibmdiagrams.ibmcloud.connectors import *
from ibmdiagrams.ibmcloud.data import *
from ibmdiagrams.ibmcloud.devops import *
from ibmdiagrams.ibmcloud.observability import *
from ibmdiagrams.ibmcloud.security import *
from ibmdiagrams.ibmcloud.groups import *

with Diagram("golden-gate-glory"):
  with PublicNetwork("Public Network", direction="TB"):
    repo = SourceCodeRepository("Information")
    engineer = User("Engineer")
    repo >> engineer
    veteran = User("Veteran")
  with IBMCloud("IBM Cloud", direction="TB"):
    with Region("Dallas", direction="TB"):
      with watsonx("watsonx", direction="TB"):
        with watsonxAI("watsonx AI", "Build Solutions"):
          promptlab = WatsonStudio("Prompt Lab")
          engineer >> promptlab
          with ExpandedApplication("RAG"):
            creation = CloudLogs("Creation")
            retrieval = CloudLogs("Search/Retrieval")
            augmentation = CloudLogs("Augmentation")
            vdb = Database("Vector DB")
            llm = Database("Granite LLM")
            creation >> retrieval
            retrieval >> augmentation
            augmentation >> vdb
            vdb >> llm
            #response = CloudLogs("Response", "Generation")
            #llm >> response

          promptlab >> SolidEdge("Query") >> creation
          output = CloudLogs("Output")
          llm >> SolidEdge("Reply") >> output

        with watsonxOrchestrate("watsonx Orch", "Manage Agents") as orchestrate:
          engineeragent = WatsonStudio("Agent", "Engineer")
          veteranagent = WatsonStudio("Agent", "Veteran")
          engineer >> engineeragent
          veteran >> veteranagent
          with ExpandedApplication("Veteran Agents", direction="TB") as veteranagents:
            armyagent = WatsonStudio("Agent", "Army")
            navyagent = WatsonStudio("Agent", "Navy")
            marinecorpsagent = WatsonStudio("Agent", "Marine Corps")
            airforceagent = WatsonStudio("Agent", "Air Force")
            spaceforceagent = WatsonStudio("Agent", "Space Force")
            coastguardagent = WatsonStudio("Agent", "Coast Guard")
          veteranagent >> SolidEdge("Query") >> veteranagents
          with ExpandedApplication("Backend Agents", direction="TB") as backendagents:
            with ExpandedApplication("RAG") as rag:
              ingestoragent = WatsonStudio("Agent", "Ingestor")
              engineeragent >> SolidEdge("Setup") >> veteranagents
              veteranagents >> rag
              vdb = Database("Vector DB")
              ingestoragent >> vdb
              llm = Database("Granite LLM")
              vdb >> llm
            with ExpandedApplication("Response") as response:
              retrieveragent = WatsonStudio("Agent", "Retriever")
              synthesizeragent = WatsonStudio("Agent", "Synthesizer")
              retrieveragent >> synthesizeragent
              validatoragent = WatsonStudio("Agent", "Validator")
              synthesizeragent >> validatoragent
            rag >> response
            reply = CloudLogs("Output")
            response >> reply
            reply >> SolidEdge("Reply") >> veteranagent
            #response >> SolidEdge("Reply") >> reply
            #metadataagent = WatsonStudio("Metadata")

        with watsonxGovernance("watsonx Govern", "Governance AI") as governance:
          observabilty = Monitoring("Observability", "Alerts/Errors")
          compliance = Monitoring("Compliance", "Audits/Traces")
          lifecycle = Monitoring("Lifecycle", "Deploy/Version")
          inventory = Monitoring("Inventory", "Agents/Tools")

        governance >> orchestrate 
