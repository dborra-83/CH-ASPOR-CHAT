{
  "Objective": "Diseñar un sistema serverless que procese documentos legales con una interfaz de chat moderna y capacidades de análisis inteligente mediante modelos seleccionables.",
  "PersonaDetails": {
    "TargetUsers": ["Analistas legales", "Trabajadores sociales", "Equipos jurídicos"],
    "TechnicalProfile": "Desarrolladores full-stack con conocimientos en AWS, CDK, Next.js y procesamiento de lenguaje natural"
  },
  "TaskInstructions": {
    "Frontend": {
      "Frameworks": ["Next.js", "Tailwind CSS"],
      "UIFramework": "Tabler UI (como base visual moderna para dashboards y portales)",
      "Features": [
        "Carga de archivos PDF, DOCX o imagen",
        "Selector de modelo (Contragarantías o Informe Social)",
        "Botón de procesamiento",
        "Visualización del resultado en vista tipo chat",
        "Botón para copiar resultado al portapapeles",
        "Sección de historial de procesamiento por usuario"
      ]
    },
    "Backend": {
      "Stack": ["AWS Lambda", "Amazon Textract", "Amazon Bedrock"],
      "Flow": [
        "Guardar archivo en S3 mediante presigned URL",
        "Lambda de extracción invoca Textract",
        "Guardar texto y estado de ejecución en DynamoDB",
        "Lambda de análisis invoca Bedrock (Claude Sonnet) con prompt específico",
        "Guardar respuesta en DynamoDB con metadatos",
        "Frontend consulta el endpoint `/runs/{id}` para mostrar estado y resultado"
      ]
    }
  },
  "UseCases": [
    {
      "Name": "Contragarantías",
      "Description": "Análisis detallado de documentos para identificar compromisos de respaldo en contratos legales.",
      "TargetOutcome": "Facilitar la revisión automática de condiciones de contragarantía."
    },
    {
      "Name": "Informes Sociales",
      "Description": "Procesamiento de informes socioeconómicos para asistencia y evaluación institucional.",
      "TargetOutcome": "Obtener insights estructurados de textos largos en contextos sociales complejos."
    }
  ],
  "Architecture": {
    "IaC": "AWS CDK (Python)",
    "Region": "us-east-1",
    "Services": {
      "S3": "Almacenamiento de archivos y resultados",
      "DynamoDB": "Tracking detallado de ejecuciones y resultados",
      "Lambda": "Funciones para extracción y análisis",
      "Textract": "OCR para documentos",
      "Bedrock": "Modelo Claude 3 Sonnet",
      "API Gateway": "Exposición de endpoints backend",
      "CloudFront": "Distribución CDN para frontend"
    }
  },
  "ProjectStructure": {
    "RootFolder": "aspor-intelligence/",
    "Subfolders": {
      "cdk/": {
        "app.py": "Punto de entrada CDK",
        "stacks/": {
          "storage_stack.py": "S3 + DynamoDB",
          "api_stack.py": "API Gateway + Lambdas",
          "frontend_stack.py": "CloudFront + S3 static hosting"
        }
      },
      "backend/": {
        "extract_lambda.py": "Función Lambda para extracción con Textract",
        "analyze_lambda.py": "Función Lambda para análisis con Bedrock",
        "common/": "Funciones auxiliares (sanitize, tracking, etc.)"
      },
      "frontend/": {
        "pages/index.tsx": "Página principal con interfaz Next.js",
        "components/": {
          "Chat.tsx": "Vista tipo chat",
          "FileUploader.tsx": "Componente para subida de archivos",
          "ModelSelector.tsx": "Selector de modelo A o B",
          "CopyButton.tsx": "Botón para copiar resultado",
          "HistoryViewer.tsx": "Componente para mostrar historial por usuario"
        },
        "styles/globals.css": "Estilos generales con Tailwind CSS"
      },
      "prompts/": {
        "CONTRAGARANTIAS.txt": "Prompt Modelo A",
        "INFORMES_SOCIALES.txt": "Prompt Modelo B"
      }
    }
  },
  "ExecutionFlow": [
    "Usuario sube archivo → presigned URL hacia S3",
    "Lambda extract → usa Textract → guarda texto extraído en DynamoDB",
    "Tracking en DynamoDB cambia estado a: UPLOADED → EXTRACTED",
    "Lambda analyze → selecciona prompt según modelo A o B → invoca Bedrock",
    "Respuesta de Bedrock guardada con timestamp, modelo y texto completo",
    "Frontend consulta `/runs/{id}` periódicamente para mostrar resultado",
    "Usuario puede copiar el resultado con un solo clic",
    "Usuario accede al historial de procesamiento para revisar ejecuciones anteriores"
  ],
  "ProcessingHistory": {
    "Purpose": "Permitir a los usuarios revisar fácilmente el contenido y resultados de ejecuciones pasadas.",
    "Storage": "DynamoDB (tabla de tracking) y S3 (archivos originales)",
    "AccessMethod": "Consulta por usuario (pk = USER#web-user) mediante endpoint GET `/history/{userId}`",
    "FrontendComponent": "HistoryViewer.tsx muestra una tabla o cards con:",
    "FieldsShown": [
      "Fecha de procesamiento",
      "Modelo usado (A o B)",
      "Nombre del archivo original",
      "Cantidad de caracteres extraídos",
      "Estado actual (COMPLETED / FAILED)",
      "Botón para ver análisis completo"
    ]
  },
  "DynamoDBSchemaExample": {
    "pk": "USER#web-user",
    "sk": "RUN#20250828120000#uuid",
    "runId": "uuid-here",
    "status": "COMPLETED",
    "model": "A",
    "files": ["s3://bucket/file1.pdf"],
    "textExtracted": "10.532 caracteres",
    "bedrockResult": "[análisis completo guardado]",
    "processedAt": "2025-08-28T12:10:00Z"
  },
  "PromptValidation": {
    "AllowedModels": {
      "A": "Contragarantías → contenido de CONTRAGARANTIAS.txt",
      "B": "Informes Sociales → contenido de INFORMES_SOCIALES.txt"
    },
    "Instructions": "Cada invocación de Bedrock debe usar exactamente el prompt correspondiente, concatenado con el texto extraído (sin modificaciones)."
  },
  "ConstraintsAndValidations": {
    "MaxCharacters": 15000,
    "NoExport": true,
    "CopyOnly": true,
    "PromptsStrict": true,
    "IaCOnlyCDK": true
  },
  "ScalabilityAndCost": {
    "ExpectedUsers": "<= 10",
    "MaxDocumentsPerMonth": 100,
    "OptimizationGoal": "Minimizar costos usando servicios serverless de AWS sin comprometer calidad de análisis",
    "CostControlMechanisms": [
      "Uso de Textract en modo por demanda",
      "Lambdas con timeout reducido y capas compartidas",
      "Bedrock solo invocado bajo demanda según tipo de modelo",
      "Infraestructura provisionada con mínimo throughput en DynamoDB (on-demand)"
    ]
  },
  "Methodologies": {
    "PromptChangeTracking": {
      "Description": "Crear y mantener un archivo 'changing_prompt.md' o JSON donde se documenten todos los cambios realizados en los prompts del sistema.",
      "Purpose": "Facilitar el mantenimiento, auditoría y versionado de la lógica del análisis basado en LLMs."
    },
    "MasterPromptStrategy": {
      "Description": "Mantener un prompt maestro sincronizado con los cambios del negocio para cada tipo de modelo (A y B).",
      "Purpose": "Actuar como fuente única de verdad en todo el proyecto para futuras integraciones."
    },
    "UXDesign": {
      "Recommendation": "Adoptar componentes y estilo de diseño de Tabler UI para interfaces limpias y modernas en Next.js.",
      "Impact": "Aumentar la percepción de profesionalismo y usabilidad en el portal de análisis documental."
    }
  }
}
