# ASPOR Intelligence

Sistema serverless de procesamiento inteligente de documentos legales y sociales con interfaz de chat moderna.

## 📋 Descripción

ASPOR Intelligence es una plataforma que permite el análisis automatizado de documentos mediante IA, especializada en:
- **Contragarantías**: Análisis detallado de documentos legales y compromisos de respaldo
- **Informes Sociales**: Procesamiento de informes socioeconómicos para evaluación institucional

## 🏗️ Arquitectura

### Stack Tecnológico
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Tabler UI
- **Backend**: AWS Lambda (Python 3.11)
- **Infraestructura**: AWS CDK (Python)
- **Servicios AWS**:
  - S3: Almacenamiento de documentos
  - DynamoDB: Tracking de ejecuciones
  - Textract: Extracción de texto (OCR)
  - Bedrock: Análisis con Claude 3 Sonnet
  - CloudFront: CDN para distribución
  - API Gateway: Endpoints REST

## 🚀 Instalación y Despliegue

### Prerequisitos
- AWS CLI configurado
- Python 3.11+
- Node.js 18+
- AWS CDK CLI (`npm install -g aws-cdk`)

### 1. Configuración del Backend

```bash
cd cdk
python -m venv .venv
.venv\Scripts\activate  # En Windows
# source .venv/bin/activate  # En Linux/Mac
pip install -r requirements.txt
```

### 2. Configuración del Frontend

```bash
cd frontend
npm install
```

### 3. Despliegue con CDK

```bash
cd cdk
cdk bootstrap  # Solo la primera vez
cdk deploy --all
```

### 4. Configuración de Prompts en S3

Después del despliegue, sube los archivos de prompts al bucket S3:

```bash
aws s3 cp ../prompts/CONTRAGARANTIAS.txt s3://aspor-intelligence-documents/prompts/
aws s3 cp ../prompts/INFORMES_SOCIALES.txt s3://aspor-intelligence-documents/prompts/
```

## 📁 Estructura del Proyecto

```
aspor-intelligence/
├── cdk/                    # Infraestructura como código
│   ├── app.py             # Punto de entrada CDK
│   └── stacks/            # Stacks de infraestructura
│       ├── storage_stack.py
│       ├── api_stack.py
│       └── frontend_stack.py
├── backend/               # Funciones Lambda
│   ├── extract_lambda.py # Extracción con Textract
│   ├── analyze_lambda.py # Análisis con Bedrock
│   ├── presigned_lambda.py
│   ├── history_lambda.py
│   └── status_lambda.py
├── frontend/              # Aplicación Next.js
│   ├── pages/            # Páginas de la aplicación
│   ├── components/       # Componentes React
│   └── styles/           # Estilos CSS
├── prompts/              # Templates de prompts
│   ├── CONTRAGARANTIAS.txt
│   └── INFORMES_SOCIALES.txt
└── docs/                 # Documentación
    └── changing_prompt.md
```

## 🔄 Flujo de Procesamiento

1. **Carga de Archivo**: Usuario sube PDF/DOCX/imagen
2. **Almacenamiento**: Archivo guardado en S3 vía presigned URL
3. **Extracción**: Lambda invoca Textract para OCR
4. **Análisis**: Lambda invoca Bedrock con prompt específico
5. **Resultado**: Respuesta mostrada en interfaz tipo chat
6. **Historial**: Almacenamiento en DynamoDB para consulta posterior

## 📊 Esquema de DynamoDB

```json
{
  "pk": "USER#web-user",
  "sk": "RUN#2025-08-28T12:00:00#uuid",
  "runId": "uuid",
  "status": "COMPLETED|FAILED|PROCESSING",
  "model": "A|B",
  "fileKey": "s3://path/to/file",
  "textExtracted": "10,532 caracteres",
  "bedrockResult": "[análisis completo]",
  "processedAt": "2025-08-28T12:10:00Z"
}
```

## 🔧 Configuración de Desarrollo Local

### Frontend Development

```bash
cd frontend
npm run dev  # Servidor en http://localhost:3000
```

### Variables de Entorno

Crear archivo `.env.local` en frontend/:

```
NEXT_PUBLIC_API_URL=https://api-gateway-url.amazonaws.com
```

## 📈 Límites y Costos

- **Usuarios esperados**: ≤10
- **Documentos/mes**: ~100
- **Límite de texto**: 15,000 caracteres por documento
- **Timeout Lambda**: 5 min (extract), 10 min (analyze)

## 🔐 Seguridad

- Bucket S3 privado con acceso solo vía presigned URLs
- CORS configurado en API Gateway y S3
- CloudFront con HTTPS obligatorio
- DynamoDB con encriptación en reposo

## 🛠️ Mantenimiento

### Actualización de Prompts

1. Modificar archivo en `/prompts/`
2. Subir a S3: `aws s3 cp prompts/[archivo].txt s3://aspor-intelligence-documents/prompts/`
3. Documentar cambio en `/docs/changing_prompt.md`

### Monitoreo

- CloudWatch Logs para todas las Lambdas
- Métricas de API Gateway
- Alertas de DynamoDB

## 📝 Notas de Implementación

- El sistema usa Textract para OCR, asegurando compatibilidad con documentos escaneados
- Bedrock con Claude 3 Sonnet proporciona análisis de alta calidad
- La interfaz tipo chat facilita la interacción y revisión de resultados
- El historial permite auditoría y revisión de procesamiento anteriores

## 🤝 Contribución

Para contribuir al proyecto:
1. Documentar cambios en prompts en `changing_prompt.md`
2. Mantener la estructura de código existente
3. Actualizar este README con cambios significativos

## 📄 Licencia

Proyecto interno ASPOR - Todos los derechos reservados.