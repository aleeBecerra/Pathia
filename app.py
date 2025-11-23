from flask import Flask, render_template, request, jsonify
import csv
import json
import re
from collections import defaultdict, deque

app = Flask(__name__)

class GrafoCurricular:
    def __init__(self):
        self.grafo = defaultdict(list)  # grafo global
        self.cursos = {}  # clave: (curso, carrera), valor: info del curso
        self.carreras = set()
        
    def cargar_csv(self, archivo_csv):
        """Carga los datos del dataset y construye el grafo"""
        with open(archivo_csv, 'r', encoding='utf-8-sig') as file:
            lines = file.readlines()
            
            for i, line in enumerate(lines):
                if i == 0:  # Saltar encabezado
                    continue
                
                line = line.strip()
                if not line:
                    continue
                
                # Extraer TODOS los valores entre comillas
                valores = re.findall(r'"([^"]*)"', line)
                
                if len(valores) < 4:
                    continue
                
                # El primero es curso, los últimos 2 son nivel y carrera
                curso = valores[0].strip()
                nivel = valores[-2].strip()
                carrera = valores[-1].strip()
                
                # Los prerrequisitos son todos los valores del medio
                if len(valores) == 4:
                    # Caso simple: solo 1 prerrequisito
                    prerrequisitos_campo = valores[1].strip()
                    prereqs_lista = [valores[1].strip()] if valores[1].strip().lower() != 'ninguno' else []
                else:
                    # Múltiples prerrequisitos
                    prerrequisitos_campo = ' '.join(valores[1:-2])
                    prereqs_lista = [v.strip() for v in valores[1:-2]]
                
                # Guardar información del curso con clave compuesta (curso, carrera)
                clave = (curso, carrera)
                self.cursos[clave] = {
                    'curso': curso,
                    'nivel': nivel,
                    'carrera': carrera,
                    'prerrequisitos': prerrequisitos_campo
                }
                
                # Agregar carrera al conjunto (solo si no está vacía)
                if carrera and carrera.strip() and carrera.strip() != ',':
                    self.carreras.add(carrera)
                
                # Construir grafo dirigido (prerrequisito -> curso) dentro de la misma carrera
                for prereq in prereqs_lista:
                    prereq = prereq.strip()
                    if prereq and prereq.lower() != 'ninguno':
                        # Usar clave compuesta para el grafo también
                        prereq_key = (prereq, carrera)
                        self.grafo[prereq_key].append(clave)
    
    def filtrar_por_carrera(self, carrera):
        """Filtra el grafo por carrera específica"""
        # Filtrar cursos por carrera (clave es (curso, carrera))
        cursos_carrera = {clave: info for clave, info in self.cursos.items() 
                         if clave[1] == carrera}
        
        grafo_carrera = defaultdict(list)
        # Incluir TODOS los cursos de la carrera
        for clave in cursos_carrera:
            grafo_carrera[clave] = []
        
        # Agregar las conexiones entre cursos de la misma carrera
        for clave in cursos_carrera:
            if clave in self.grafo:
                grafo_carrera[clave] = [c for c in self.grafo[clave] 
                                       if c in cursos_carrera]
        
        return cursos_carrera, grafo_carrera
    
    def dfs(self, nodo, visitados, grafo):
        """Algoritmo DFS para recorrer el grafo"""
        visitados.add(nodo)
        camino = [nodo]
        
        if nodo in grafo:
            for vecino in grafo[nodo]:
                if vecino not in visitados:
                    camino.extend(self.dfs(vecino, visitados, grafo))
        
        return camino
    
    def detectar_ciclos(self, grafo):
        """Detecta ciclos en el grafo usando DFS"""
        visitados = set()
        recursion_stack = set()
        
        def dfs_ciclo(nodo):
            visitados.add(nodo)
            recursion_stack.add(nodo)
            
            if nodo in grafo:
                for vecino in grafo[nodo]:
                    if vecino not in visitados:
                        if dfs_ciclo(vecino):
                            return True
                    elif vecino in recursion_stack:
                        return True
            
            recursion_stack.remove(nodo)
            return False
        
        for curso in grafo:
            if curso not in visitados:
                if dfs_ciclo(curso):
                    return True
        return False
    
    def ordenamiento_topologico(self, cursos_carrera, grafo_carrera):
        """Implementa ordenamiento topológico usando algoritmo de Kahn"""
        # Calcular grado de entrada para cada nodo
        grado_entrada = {curso: 0 for curso in cursos_carrera}
        
        for curso in grafo_carrera:
            for vecino in grafo_carrera[curso]:
                grado_entrada[vecino] += 1
        
        # Para nodos sin prerrequisitos
        for curso in cursos_carrera:
            prereqs = cursos_carrera[curso]['prerrequisitos']
            if prereqs.lower() == 'ninguno' and curso not in grado_entrada:
                grado_entrada[curso] = 0
        
        # Cola con nodos sin dependencias
        cola = deque([curso for curso, grado in grado_entrada.items() if grado == 0])
        orden = []
        
        while cola:
            nodo = cola.popleft()
            # Extraer solo el nombre del curso (nodo es una tupla (curso, carrera))
            orden.append(nodo[0] if isinstance(nodo, tuple) else nodo)
            
            if nodo in grafo_carrera:
                for vecino in grafo_carrera[nodo]:
                    grado_entrada[vecino] -= 1
                    if grado_entrada[vecino] == 0:
                        cola.append(vecino)
        
        return orden if len(orden) == len(cursos_carrera) else None

# Inicializar grafo
grafo_global = GrafoCurricular()
grafo_global.cargar_csv('datasetvf_1.txt')

@app.route('/')
def index():
    """Página principal con las 4 opciones"""
    return render_template('index.html')

@app.route('/grafo')
def grafo():
    """Página para visualizar el grafo"""
    carreras = list(grafo_global.carreras)
    return render_template('grafo.html', carreras=carreras)

@app.route('/api/grafo/<carrera>')
def api_grafo(carrera):
    """API para obtener datos del grafo de una carrera"""
    cursos_carrera, grafo_carrera = grafo_global.filtrar_por_carrera(carrera)
    
    # Verificar ciclos
    tiene_ciclos = grafo_global.detectar_ciclos(grafo_carrera)
    
    # Ordenamiento topológico
    orden_topologico = None
    if not tiene_ciclos:
        orden_topologico = grafo_global.ordenamiento_topologico(cursos_carrera, grafo_carrera)
    
    # Preparar datos para visualización
    # clave es (curso, carrera), extraer solo el nombre del curso
    nodos = []
    for clave, info in cursos_carrera.items():
        curso_nombre = clave[0]  # Extraer nombre del curso de la tupla
        nodos.append({
            'id': curso_nombre,
            'label': curso_nombre,
            'nivel': info['nivel'],
            'carrera': info['carrera']
        })
    
    # Crear aristas usando el grafo ya construido
    aristas = []
    for prereq_key, cursos_siguientes in grafo_carrera.items():
        prereq_nombre = prereq_key[0]  # Extraer nombre del prerrequisito
        for curso_key in cursos_siguientes:
            curso_nombre = curso_key[0]  # Extraer nombre del curso
            aristas.append({
                'from': prereq_nombre,
                'to': curso_nombre
            })
    
    return jsonify({
        'nodos': nodos,
        'aristas': aristas,
        'tiene_ciclos': tiene_ciclos,
        'orden_topologico': orden_topologico
    })

@app.route('/desbloqueados')
def desbloqueados():
    """Página para consultar cursos desbloqueados"""
    return render_template('desbloqueados.html')

@app.route('/api/carreras')
def api_carreras():
    """API para obtener lista de carreras"""
    # Filtrar carreras vacías o que solo contengan espacios/comas
    carreras_validas = [c for c in grafo_global.carreras if c and c.strip() and c.strip() != ',']
    return jsonify({
        'carreras': sorted(carreras_validas)
    })

@app.route('/api/cursos/<carrera>')
def api_cursos_carrera(carrera):
    """Obtener cursos de una carrera específica"""
    cursos_carrera, _ = grafo_global.filtrar_por_carrera(carrera)
    
    # Crear diccionario simple: curso_nombre -> nivel
    cursos_dict = {}
    for clave, info in cursos_carrera.items():
        curso_nombre = clave[0]
        cursos_dict[curso_nombre] = info['nivel']
    
    return jsonify({
        'cursos': cursos_dict
    })

@app.route('/api/desbloqueados/<carrera>/<curso>')
def api_desbloqueados(carrera, curso):
    """API para obtener cursos que se desbloquean al aprobar un curso (por niveles)"""
    cursos_carrera, grafo_carrera = grafo_global.filtrar_por_carrera(carrera)
    
    # Buscar la clave del curso seleccionado
    curso_key = (curso, carrera)
    
    # BFS para obtener cursos por niveles
    desbloqueados_por_nivel = {}
    total_desbloqueados = 0
    
    if curso_key in grafo_carrera:
        from collections import deque
        
        cola = deque([(curso_key, 0)])  # (nodo, nivel)
        visitados = {curso_key}
        
        while cola:
            nodo_actual, nivel_actual = cola.popleft()
            
            # Obtener vecinos del nodo actual
            if nodo_actual in grafo_carrera:
                for vecino_key in grafo_carrera[nodo_actual]:
                    if vecino_key not in visitados:
                        visitados.add(vecino_key)
                        
                        # Agregar al nivel correspondiente
                        nivel = nivel_actual + 1
                        if nivel not in desbloqueados_por_nivel:
                            desbloqueados_por_nivel[nivel] = []
                        
                        curso_nombre = vecino_key[0]
                        info = cursos_carrera[vecino_key]
                        desbloqueados_por_nivel[nivel].append({
                            'curso': curso_nombre,
                            'nivel': info['nivel'],
                            'prerrequisitos': info['prerrequisitos']
                        })
                        
                        total_desbloqueados += 1
                        cola.append((vecino_key, nivel))
    
    return jsonify({
        'curso_base': curso,
        'desbloqueados_por_nivel': desbloqueados_por_nivel,
        'total_desbloqueados': total_desbloqueados
    })

@app.route('/recomendacion')
def recomendacion():
    return render_template('recomendacion.html')

@app.route('/prerrequisitos')
def prerrequisitos():
    return render_template('prerrequisitos.html')

@app.route('/api/prerrequisitos/<carrera>/<path:curso>')
def api_prerrequisitos(carrera, curso):
    """
    Obtener los prerrequisitos inmediatos de un curso.
    Usa búsqueda directa en la estructura del grafo.
    """
    try:
        # Filtrar cursos por carrera
        cursos_carrera, _ = grafo_global.filtrar_por_carrera(carrera)
        
        # Buscar el curso (normalizado, case-insensitive)
        curso_key = None
        curso_encontrado = None
        
        for clave, info in cursos_carrera.items():
            if clave[0].lower() == curso.lower():
                curso_key = clave
                curso_encontrado = clave[0]
                break
        
        if not curso_key:
            return jsonify({'error': 'Curso no encontrado en esta carrera'}), 404
        
        # Obtener prerrequisitos del curso
        info_curso = cursos_carrera[curso_key]
        prereqs_str = info_curso['prerrequisitos']
        
        # Verificar si es un prerrequisito especial (créditos, etc.)
        requisitos_especiales = ['credito', 'creditos', 'aprobado', 'director', 'ingles', 'todos los cursos']
        es_requisito_especial = any(palabra in prereqs_str.lower() for palabra in requisitos_especiales)
        
        if not prereqs_str or prereqs_str.lower() == 'ninguno' or es_requisito_especial:
            mensaje_especial = None
            if es_requisito_especial:
                mensaje_especial = f"Este curso tiene un requisito especial: {prereqs_str}"
            
            return jsonify({
                'curso': curso_encontrado,
                'tiene_prerrequisitos': False,
                'prerrequisitos': [],
                'total': 0,
                'nivel_curso': info_curso['nivel'],
                'mensaje_especial': mensaje_especial
            })
        
        # Parsear prerrequisitos
        prereqs_list = []
        
        # Primero intentar extraer por comillas (formato: "prereq1" "prereq2")
        prereqs_quoted = re.findall(r'"([^"]+)"', prereqs_str)
        if prereqs_quoted:
            prereqs_list = [p.strip() for p in prereqs_quoted if p.strip() and p.strip().lower() != 'ninguno']
        else:
            # Si no hay comillas, buscar coincidencias con los cursos de la carrera
            prereqs_list = []
            texto_restante = prereqs_str
            
            # Obtener todos los nombres de cursos de la carrera
            nombres_cursos = [k[0] for k in cursos_carrera.keys()]
            # Ordenar por longitud descendente para buscar primero los nombres más largos
            nombres_cursos.sort(key=len, reverse=True)
            
            # Buscar cada nombre de curso en el texto de prerrequisitos
            for nombre_curso in nombres_cursos:
                if nombre_curso.lower() in texto_restante.lower():
                    prereqs_list.append(nombre_curso)
                    # Remover el curso encontrado del texto para evitar duplicados
                    texto_restante = texto_restante.lower().replace(nombre_curso.lower(), '', 1)
        
        # Obtener información completa de cada prerrequisito
        prerrequisitos_info = []
        for prereq in prereqs_list:
            prereq_key = (prereq, carrera)
            if prereq_key in cursos_carrera:
                prereq_info = cursos_carrera[prereq_key]
                prerrequisitos_info.append({
                    'curso': prereq,
                    'nivel': prereq_info['nivel']
                })
            else:
                # Si no se encuentra, agregarlo sin nivel
                prerrequisitos_info.append({
                    'curso': prereq,
                    'nivel': 'N/A'
                })
        
        return jsonify({
            'curso': curso_encontrado,
            'tiene_prerrequisitos': True,
            'prerrequisitos': prerrequisitos_info,
            'total': len(prerrequisitos_info),
            'nivel_curso': info_curso['nivel']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recomendar/<carrera>', methods=['POST'])
def api_recomendar(carrera):
    """
    Recomendador inteligente usando Algoritmo de Kahn modificado.
    Recibe los cursos aprobados y retorna los cursos disponibles para matricular.
    """
    try:
        data = request.get_json()
        cursos_aprobados = set(data.get('cursos_aprobados', []))
        
        # Filtrar cursos por carrera
        cursos_carrera, grafo_carrera = grafo_global.filtrar_por_carrera(carrera)
        
        if not cursos_carrera:
            return jsonify({'error': 'No se encontraron cursos para esta carrera'}), 404
        
        # Aplicar Algoritmo de Kahn modificado
        # Calcular grado de entrada para cada curso (excluyendo cursos aprobados)
        grado_entrada = {}
        
        # Inicializar grados de entrada para todos los cursos NO aprobados
        for curso_key in cursos_carrera.keys():
            curso_nombre = curso_key[0]
            if curso_nombre not in cursos_aprobados:
                grado_entrada[curso_nombre] = 0
        
        # Calcular grados de entrada basados en prerrequisitos NO aprobados
        for curso_key, info in cursos_carrera.items():
            curso_nombre = curso_key[0]
            
            # Si el curso ya está aprobado, no lo consideramos
            if curso_nombre in cursos_aprobados:
                continue
            
            # Contar cuántos prerrequisitos NO aprobados tiene
            prereqs_str = info['prerrequisitos']
            if prereqs_str and prereqs_str.lower() != 'ninguno':
                prereq_list = [p.strip() for p in prereqs_str.split(',')]
                for prereq in prereq_list:
                    # Solo contar si el prerrequisito NO está aprobado
                    if prereq not in cursos_aprobados:
                        # Verificar que el prerrequisito existe en la carrera
                        prereq_key = (prereq, carrera)
                        if prereq_key in cursos_carrera:
                            grado_entrada[curso_nombre] += 1
        
        # Los cursos disponibles son aquellos con grado de entrada 0
        cursos_disponibles = []
        for curso_nombre, grado in grado_entrada.items():
            if grado == 0:
                curso_key = (curso_nombre, carrera)
                if curso_key in cursos_carrera:
                    info = cursos_carrera[curso_key]
                    cursos_disponibles.append({
                        'curso': curso_nombre,
                        'nivel': info['nivel'],
                        'prerrequisitos': info['prerrequisitos']
                    })
        
        # Agrupar por ciclo/nivel
        por_nivel = {}
        for curso in cursos_disponibles:
            nivel = curso['nivel']
            if nivel not in por_nivel:
                por_nivel[nivel] = []
            por_nivel[nivel].append(curso)
        
        # Estadísticas
        total_cursos = len(cursos_carrera)
        cursos_completados = len(cursos_aprobados)
        progreso = (cursos_completados / total_cursos * 100) if total_cursos > 0 else 0
        
        return jsonify({
            'cursos_disponibles': cursos_disponibles,
            'por_nivel': por_nivel,
            'total_disponibles': len(cursos_disponibles),
            'estadisticas': {
                'total_cursos': total_cursos,
                'cursos_aprobados': cursos_completados,
                'progreso': round(progreso, 1),
                'cursos_pendientes': total_cursos - cursos_completados
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
