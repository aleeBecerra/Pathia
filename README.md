# PATHIA - Sistema de Gestión Curricular

Sistema web para visualización y análisis de mallas curriculares usando grafos dirigidos.

## Características

- **Visualización de Grafo Curricular**: Representa cursos y sus prerrequisitos como un grafo dirigido
- **Algoritmo DFS**: Recorrido en profundidad para explorar la estructura curricular
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

## Estructura del Proyecto

- `app.py` - Aplicación Flask con lógica del grafo
- `cursosmallaof.csv` - Datos de cursos (UTF-8)
- `templates/` - Plantillas HTML
  - `index.html` - Página principal con 4 opciones
  - `grafo.html` - Visualización del grafo
- `requirements.txt` - Dependencias del proyecto

## Formato del CSV

```csv
"curso","prerrequisitos","nivel","carrera"
"Nombre del Curso","Curso1;Curso2","Ciclo 1","Nombre Carrera"
```

- Prerrequisitos múltiples se separan con `;`
- Use "Ninguno" para cursos sin prerrequisitos

## Uso

1. Selecciona una carrera del menú principal
2. Haz clic en "Grafo" para visualizar
3. El sistema mostrará:
   - Grafo visual con nodos (cursos) y aristas (prerrequisitos)
   - Detección de ciclos
   - Orden topológico sugerido

## Tecnologías

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript
- **Visualización**: Vis.js Network
- **Algoritmos**: DFS, Ordenamiento Topológico (Kahn)
