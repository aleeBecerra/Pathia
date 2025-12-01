# PATHIA - Sistema de Gestión Curricular

Aplicación web para visualización y análisis de mallas curriculares usando grafos dirigidos.

## Características

- **Visualización de Grafo Curricular**: Representa cursos y sus prerrequisitos como un grafo dirigido
- **Algoritmo DFS**: Recorrido en profundidad para explorar la estructura curricular
- **Algoritmo BFS**: Identifica todos los cursos que se desbloquean al aprobar uno específico, agrupándolos por niveles de distancia.
- **Detección de Ciclos**: Identifica dependencias circulares en la malla
- **Ordenamiento Topológico**: Genera secuencias válidas de cursos respetando prerrequisitos
- **Filtrado por Carrera**: Visualiza solo los cursos de una carrera específica

## Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Ejecutar la aplicación:
```bash
python app.py
```

3. Abrir en el navegador: http://127.0.0.1:5000

## Despliegue
Link de aplicación desplegada: https://pathia-ciyd.onrender.com
## Formato del Data Set

```csv
"curso", "créditos", "prerrequisitos","nivel","carrera"
```
