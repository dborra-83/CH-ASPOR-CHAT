# ASPOR Intelligence - Sistema de Análisis de Documentos con IA

Sistema empresarial de análisis inteligente de documentos legales y sociales utilizando AWS y Claude 3.5 Sonnet.

## 🚀 Características

- **Análisis Inteligente con IA**: Utiliza Claude 3.5 Sonnet para análisis profundo de documentos
- **Procesamiento Asíncrono**: Maneja documentos grandes sin timeouts (hasta 5 minutos de procesamiento)
- **Doble Modo de Análisis**:
  - **Contragarantías**: Análisis de documentos legales y garantías
  - **Informes Sociales**: Evaluación socioeconómica y planes de intervención
- **Visión por Computadora**: Procesa PDFs escaneados e imágenes directamente
- **Interfaz Web Moderna**: React/Next.js con diseño responsivo y animaciones fluidas
- **Chat Profesional**: Resultados de IA con formato rico y tipografía optimizada
- **Historial Interactivo**: Búsqueda y filtros dinámicos para encontrar análisis previos
- **Indicadores en Tiempo Real**: Visualización clara del progreso de procesamiento
- **Escalable**: Arquitectura serverless en AWS

## 📋 Requisitos Previos

- Node.js 18+ y npm
- Python 3.11+
- AWS CLI configurado
- AWS CDK 2.100+
- Cuenta AWS con permisos para:
  - Lambda, S3, DynamoDB
  - API Gateway, CloudFront
  - Bedrock (Claude 3.5 Sonnet)
  - Textract

## 🛠️ Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/aspor-intelligence.git
cd aspor-intelligence
```

### 2. Instalar dependencias del CDK
```bash
cd cdk
npm install
```

### 3. Instalar dependencias del Frontend
```bash
cd ../frontend
npm install
```

### 4. Configurar variables de entorno
```bash
# En frontend/.env.local
NEXT_PUBLIC_API_URL=https://tu-api-gateway-url.amazonaws.com/prod
```

### 5. Desplegar la infraestructura
```bash
cd ../cdk
cdk bootstrap  # Solo la primera vez
cdk deploy --all
```

## 🏗️ Arquitectura

### Componentes Principales

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│   Frontend   │────▶│  API Gateway    │
│  Distribution   │     │   (Next.js)  │     │                 │
└─────────────────┘     └──────────────┘     └─────────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                         Lambda Functions                      │
├─────────────────┬────────────────┬──────────────────────────┤
│  Upload Lambda  │ Extract Lambda │   Analyze Lambda         │
│  (Presigned URL)│  (Textract)    │  (Inicia async)          │
└─────────────────┴────────────────┴──────────────────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐    ┌──────────────────┐
                    │      S3      │    │ Process Async    │
                    │   Buckets    │    │    Lambda        │
                    └──────────────┘    │  (5 min timeout) │
                                        └──────────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐    ┌──────────────────┐
                    │   DynamoDB   │    │  Bedrock API     │
                    │    Table     │    │ (Claude 3.5)     │
                    └──────────────┘    └──────────────────┘
```

### Flujo de Procesamiento

1. **Carga del Documento**: Usuario sube PDF/imagen via presigned URL a S3
2. **Extracción de Texto**: 
   - Intenta con AWS Textract (3 segundos timeout)
   - Si falla, usa Bedrock Vision directamente
3. **Análisis Asíncrono**:
   - API retorna inmediatamente (202 Accepted)
   - Lambda asíncrona procesa con Claude 3.5 Sonnet
   - Frontend hace polling cada 3 segundos
4. **Resultado**: Análisis detallado hasta 10,000 caracteres

## 📁 Estructura del Proyecto

```
aspor-intelligence/
├── frontend/               # Aplicación Next.js
│   ├── pages/             # Páginas de la aplicación
│   ├── components/        # Componentes React
│   └── public/            # Assets estáticos
├── backend/               # Funciones Lambda
│   ├── extract_lambda.py # Extracción con Textract
│   ├── analyze_lambda_async.py # Iniciador asíncrono
│   ├── process_async_lambda.py # Procesador principal
│   ├── check_status_lambda.py  # Verificación de estado
│   └── presigned_lambda.py     # URLs presignadas
├── cdk/                   # Infraestructura como código
│   ├── stacks/           # Stacks de CDK
│   │   ├── storage_stack.py    # S3 y DynamoDB
│   │   ├── api_stack.py        # Lambda y API Gateway
│   │   └── frontend_stack.py   # CloudFront y S3
│   └── app.py            # Aplicación CDK principal
└── docs/                 # Documentación adicional
```

## 🔧 Configuración

### Límites del Sistema
- **Tamaño máximo de archivo**: 10MB
- **Caracteres de entrada**: 30,000
- **Caracteres de salida**: 10,000
- **Timeout de procesamiento**: 5 minutos
- **Formato soportado**: PDF

### Modelos de Análisis

#### Modelo A - Contragarantías
Analiza documentos legales identificando:
- Tipos de contragarantías
- Partes involucradas
- Condiciones específicas
- Plazos y vigencia
- Riesgos identificados

#### Modelo B - Informes Sociales
Evalúa informes sociales extrayendo:
- Situación socioeconómica
- Factores de riesgo
- Recursos disponibles
- Necesidades detectadas
- Recomendaciones de intervención
- Plan de acción sugerido

## 🚀 Uso

### Interfaz Web
1. Acceder a https://tu-cloudfront-url.cloudfront.net
2. Seleccionar un documento PDF
3. Elegir el modelo de análisis
4. Click en "Procesar Documento"
5. Esperar el resultado (10-30 segundos)

### API REST
```bash
# 1. Obtener URL de carga
curl -X POST https://api-url/upload \
  -H "Content-Type: application/json" \
  -d '{"fileName": "documento.pdf", "fileType": "application/pdf"}'

# 2. Subir archivo a S3
curl -X PUT "presigned-url" \
  --data-binary @documento.pdf

# 3. Extraer texto
curl -X POST https://api-url/extract \
  -H "Content-Type: application/json" \
  -d '{"fileKey": "uploads/xxx.pdf", "runId": "xxx"}'

# 4. Analizar documento
curl -X POST https://api-url/analyze \
  -H "Content-Type: application/json" \
  -d '{"runId": "xxx", "model": "A"}'

# 5. Verificar estado
curl https://api-url/status/xxx
```

## 🔍 Monitoreo y Debugging

### CloudWatch Logs
Los logs se encuentran en CloudWatch bajo:
- `/aws/lambda/AsporApiStack-ExtractLambda-*`
- `/aws/lambda/AsporApiStack-ProcessAsyncLambda-*`
- `/aws/lambda/AsporApiStack-AnalyzeLambda-*`

### DynamoDB
Tabla: `aspor-intelligence-executions`
- Partition Key: `pk` (USER#userId)
- Sort Key: `sk` (RUN#timestamp#runId)
- GSI: `runId-index`

### Diagnóstico
```bash
cd backend
python diagnose_flow.py [runId]
```

## 🛡️ Seguridad

- URLs presignadas con expiración de 5 minutos
- CORS configurado para dominios específicos
- IAM roles con permisos mínimos necesarios
- Sin almacenamiento de datos sensibles en logs
- Encriptación en tránsito y reposo

## 📈 Escalabilidad

- **Lambda Concurrency**: Configurada para 100 ejecuciones simultáneas
- **DynamoDB**: On-demand billing
- **S3**: Lifecycle policies para archivos antiguos
- **CloudFront**: Caché global para assets estáticos

## 🌐 Demo en Vivo

Accede a la aplicación en producción:
- **Frontend:** https://d2h1no7ln1qj3f.cloudfront.net

## 📝 Licencia

Este proyecto es propiedad de ASPOR. Todos los derechos reservados.

## 📞 Soporte

Para soporte y consultas:
- Email: soporte@aspor.com
- Issues: https://github.com/tu-usuario/aspor-intelligence/issues

## 🔄 Actualizaciones Recientes

### v2.2.0 (2024-08-29)
- ✨ **Chat Mejorado**: Nueva interfaz de chat con formato profesional
- 🎨 **Análisis con Estilo**: Resultados de IA en tarjetas elegantes con gradientes
- 📊 **Indicadores de Proceso**: Visualización en tiempo real del progreso
- 🎯 **Formato Rico**: Soporte completo de Markdown con tipografía optimizada
- ⚡ **Animaciones Fluidas**: Transiciones suaves y efectos visuales
- 🎨 **Tema Unificado**: Paleta de colores púrpura/rosa consistente

### v2.1.0 (2024-08-29)
- ✅ **Historial Mejorado**: Búsqueda y filtros dinámicos en el historial
- ✅ **Interfaz Visual Renovada**: Diseño moderno con gradientes y mejor UX
- ✅ **Corrección de Bugs**: Botón "Ver Análisis IA" ahora funciona correctamente
- ✅ **Modelo de Análisis Visible**: Ya no muestra "N/A" en el campo modelo
- ✅ **Filtros Avanzados**: Por estado (Completado/Fallido) y modelo (Contragarantías/Informes)

### v2.0.0 (2024-08-29)
- ✅ Procesamiento asíncrono para evitar timeouts
- ✅ Integración con Bedrock Vision para PDFs escaneados
- ✅ Aumento de límites: 30k entrada, 10k salida
- ✅ Polling automático en frontend
- ✅ Manejo mejorado de errores

### v1.0.0 (2024-08-28)
- 🚀 Lanzamiento inicial
- 📄 Soporte para PDF
- 🤖 Integración con Claude 3.5 Sonnet
- 📊 Dos modelos de análisis