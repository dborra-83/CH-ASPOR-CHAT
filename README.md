# ASPOR Intelligence - Sistema de Análisis de Documentos

Sistema serverless de procesamiento y análisis inteligente de documentos utilizando AWS y IA.

## 🚀 Características

- **Extracción de texto OCR** con Amazon Textract
- **Análisis con IA** usando Claude 3.5 Sonnet vía Amazon Bedrock
- **Interfaz web moderna** desarrollada con Next.js y React
- **Historial interactivo** con búsqueda y filtros dinámicos
- **Procesamiento asíncrono** sin límites de timeout
- **Arquitectura serverless** con AWS Lambda y DynamoDB
- **Distribución global** con CloudFront CDN
- **Soporte para múltiples formatos**: PDF, PNG, JPG, JPEG, DOCX

## 📁 Estructura del Proyecto

```
CH-ASPOR-CHAT/
├── aspor-intelligence/
│   ├── backend/           # Funciones Lambda
│   ├── frontend/          # Aplicación Next.js
│   └── cdk/              # Infraestructura como código
├── CONTRAGARANTIAS.txt   # Prompt para análisis de contragarantías
├── INFORMES SOCIALES.txt # Prompt para análisis de informes sociales
└── README.md
```

## 🛠️ Tecnologías

### Backend
- **AWS Lambda** - Procesamiento serverless
- **Amazon Textract** - OCR y extracción de texto
- **Amazon Bedrock** - Análisis con Claude 3 Sonnet
- **DynamoDB** - Base de datos NoSQL
- **S3** - Almacenamiento de documentos
- **API Gateway** - API REST

### Frontend
- **Next.js 14** - Framework React
- **TypeScript** - Tipado estático
- **Tailwind CSS** - Estilos utility-first
- **Tabler Icons** - Iconografía
- **Axios** - Cliente HTTP

### Infraestructura
- **AWS CDK** - Infrastructure as Code
- **CloudFront** - CDN global
- **Python 3.11** - Runtime de Lambda

## 📋 Requisitos Previos

- Node.js 18+ y npm
- Python 3.11+
- AWS CLI configurado
- AWS CDK instalado (`npm install -g aws-cdk`)
- Cuenta AWS con permisos apropiados

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/dborra-83/CH-ASPOR-CHAT.git
cd CH-ASPOR-CHAT
```

### 2. Configurar el Backend (CDK)

```bash
cd aspor-intelligence/cdk
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. Configurar el Frontend

```bash
cd ../frontend
npm install
```

### 4. Configurar variables de entorno

Crear archivo `.env.local` en `aspor-intelligence/frontend/`:

```env
NEXT_PUBLIC_API_URL=https://your-api-gateway-url/prod/
```

## 🚀 Despliegue

### 1. Desplegar la infraestructura

```bash
cd aspor-intelligence/cdk
cdk bootstrap  # Solo la primera vez
cdk deploy AsporStorageStack
cdk deploy AsporApiStack
cdk deploy AsporFrontendStack
```

### 2. Construir y desplegar el frontend

```bash
cd ../frontend
npm run build
aws s3 sync ./out/ s3://aspor-intelligence-frontend/ --delete
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

## 📖 Uso

### Análisis de Documentos
1. Acceder a la aplicación web via CloudFront URL
2. Cargar un documento (PDF o imagen)
3. Seleccionar el tipo de análisis:
   - **Modelo A**: Contragarantías
   - **Modelo B**: Informes Sociales
4. Hacer clic en "Analizar con IA"
5. Ver el resultado del análisis

### Historial de Análisis
- **Búsqueda**: Encuentra documentos por nombre o ID
- **Filtros**: Por estado (Completado/Fallido) o modelo de análisis
- **Vista de Resultados**: Click en "Ver Análisis IA" para ver el análisis completo
- **Interfaz Moderna**: Diseño con gradientes y transiciones suaves

## 🔒 Seguridad

- Todos los endpoints de API tienen CORS configurado
- Las funciones Lambda usan roles IAM con permisos mínimos
- Los documentos se almacenan en S3 con encriptación
- No se almacenan credenciales en el código

## 📊 Monitoreo

- CloudWatch Logs para todas las funciones Lambda
- Métricas de API Gateway
- Alarmas configurables en CloudWatch

## 🌐 Demo en Vivo

Accede a la aplicación en producción:
- **Frontend:** https://d2h1no7ln1qj3f.cloudfront.net

## 📝 Licencia

Este proyecto es privado y confidencial. Propiedad de ASPOR.

## 🔄 Últimas Actualizaciones

### v2.2.0 (29 de Agosto, 2024)
- 💬 **Chat Profesional**: Nueva interfaz de conversación con diseño elegante
- 🤖 **Resultados de IA Mejorados**: Análisis presentados en tarjetas con formato rico
- ⏳ **Indicadores de Progreso**: Visualización clara de cada etapa del procesamiento
- 🎨 **Diseño Unificado**: Tema coherente púrpura/rosa en toda la aplicación
- ✨ **Animaciones**: Transiciones suaves y efectos visuales profesionales

### v2.1.0 (29 de Agosto, 2024)
- ✨ **Nuevo Sistema de Búsqueda**: Busca documentos por nombre o ID de procesamiento
- 🎨 **Interfaz Renovada**: Diseño moderno con gradientes y mejor experiencia de usuario
- 🔍 **Filtros Avanzados**: Filtra por estado y modelo de análisis
- 🐛 **Correcciones**: Botón "Ver Análisis IA" funciona correctamente con procesamiento asíncrono
- 📊 **Mejoras en el Historial**: Vista mejorada con información más clara y accesible

## 👥 Contacto

Diego Borra - [@dborra-83](https://github.com/dborra-83)