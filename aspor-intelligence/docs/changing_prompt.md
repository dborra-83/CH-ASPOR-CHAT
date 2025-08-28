# Historial de Cambios en Prompts

## Propósito
Este documento registra todos los cambios realizados en los prompts del sistema ASPOR Intelligence para mantener trazabilidad y facilitar el versionado de la lógica de análisis.

## Estructura de Registro
Cada cambio debe documentarse con:
- **Fecha**: YYYY-MM-DD
- **Modelo**: A (Contragarantías) o B (Informes Sociales)
- **Versión**: Número de versión (ej: 1.0.0)
- **Cambios Realizados**: Descripción detallada
- **Razón del Cambio**: Justificación
- **Impacto Esperado**: Cómo afecta al análisis
- **Autor**: Responsable del cambio

---

## Registro de Cambios

### 2025-08-28 - Versión Inicial
**Modelos**: A y B  
**Versión**: 1.0.0  
**Autor**: Sistema

#### Modelo A - Contragarantías (v1.0.0)
**Descripción**: Prompt inicial para análisis de contragarantías en documentos legales.

**Estructura implementada**:
1. Resumen ejecutivo
2. Contragarantías identificadas
3. Análisis de condiciones
4. Evaluación de riesgos
5. Aspectos legales relevantes
6. Recomendaciones
7. Alertas y observaciones

**Características principales**:
- Análisis exhaustivo de tipos de contragarantías
- Evaluación de riesgos con niveles (Alto/Medio/Bajo)
- Identificación de partes involucradas
- Análisis de plazos y vigencia
- Recomendaciones orientadas a la acción

#### Modelo B - Informes Sociales (v1.0.0)
**Descripción**: Prompt inicial para análisis de informes socioeconómicos y evaluaciones sociales.

**Estructura implementada**:
1. Resumen del caso
2. Situación socioeconómica
3. Factores de riesgo y vulnerabilidad
4. Recursos y fortalezas
5. Necesidades detectadas
6. Plan de intervención propuesto
7. Recomendaciones específicas
8. Pronóstico y seguimiento
9. Observaciones adicionales

**Características principales**:
- Análisis integral de la situación familiar
- Clasificación de necesidades por urgencia
- Identificación de recursos disponibles
- Plan de intervención con cronograma
- Indicadores de seguimiento y éxito

---

## Guía para Futuros Cambios

### Proceso de Modificación
1. **Evaluar necesidad**: Identificar qué aspecto del análisis necesita mejora
2. **Documentar propuesta**: Describir el cambio propuesto y su justificación
3. **Testear**: Probar el nuevo prompt con casos de ejemplo
4. **Implementar**: Actualizar el archivo de prompt correspondiente
5. **Registrar**: Documentar el cambio en este archivo
6. **Versionar**: Incrementar la versión según el tipo de cambio:
   - Mayor (X.0.0): Cambios estructurales significativos
   - Menor (x.X.0): Nuevas secciones o funcionalidades
   - Parche (x.x.X): Correcciones menores o ajustes

### Consideraciones
- Mantener consistencia en el formato de salida
- Preservar la claridad y estructura del análisis
- Considerar el límite de tokens (15,000 caracteres)
- Validar que los cambios no afecten negativamente casos existentes

### Métricas de Evaluación
Para evaluar la efectividad de los cambios, considerar:
- **Completitud**: ¿El análisis cubre todos los aspectos relevantes?
- **Precisión**: ¿Las identificaciones y categorizaciones son correctas?
- **Utilidad**: ¿Las recomendaciones son accionables?
- **Claridad**: ¿El resultado es fácil de entender?
- **Consistencia**: ¿El formato se mantiene uniforme?

---

## Plantilla para Nuevos Registros

```markdown
### YYYY-MM-DD - [Título del Cambio]
**Modelo**: [A/B/Ambos]  
**Versión anterior**: X.X.X  
**Nueva versión**: X.X.X  
**Autor**: [Nombre]

**Cambios realizados**:
- [Listar cambios específicos]

**Razón del cambio**:
[Explicar la motivación]

**Impacto esperado**:
[Describir cómo mejora el análisis]

**Casos de prueba**:
[Mencionar con qué tipos de documentos se probó]

**Notas adicionales**:
[Cualquier observación relevante]
```

---

## Archivo de Versiones Anteriores
Las versiones anteriores de los prompts se mantienen en:
- `/prompts/archive/CONTRAGARANTIAS_vX.X.X.txt`
- `/prompts/archive/INFORMES_SOCIALES_vX.X.X.txt`

Esto permite rollback rápido en caso de ser necesario.