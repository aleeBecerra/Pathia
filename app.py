from flask import Flask, render_template, request, jsonify
import csv
import json
import re
from collections import defaultdict, deque

app = Flask(__name__)

class GrafoCurricular:
    def __init__(self):
        self.grafo = defaultdict(list)
        self.cursos = {}
        self.carreras = set()
        
    def cargar_csv(self, archivo_csv):
        """Carga los datos del dataset y construye el grafo"""
        with open(archivo_csv, 'r', encoding='utf-8-sig') as file:
            lines = file.readlines()
            
            for i, line in enumerate(lines):
                if i == 0:
                    continue
                
                line = line.strip()
                if not line:
                    continue
                
                valores = re.findall(r'"([^"]*)"', line)
                
                if len(valores) < 5:
                    continue
                
                curso = valores[0].strip()
                creditos = valores[1].strip()
                nivel = valores[-2].strip()
                carrera = valores[-1].strip()
                
                # Extraer prerrequisitos
                raw_prereqs = valores[2:-2]
                
                prereqs_lista = []
                for p in raw_prereqs:
                    p_limpio = p.strip()
                    if p_limpio and p_limpio.lower() != 'ninguno':
                        prereqs_lista.append(p_limpio)
                
                prerrequisitos_campo = ','.join(prereqs_lista) if prereqs_lista else 'Ninguno'
                
                # Guardar información del curso
                clave = (curso, carrera)
                self.cursos[clave] = {
                    'curso': curso,
                    'creditos': int(creditos) if creditos.isdigit() else 0,
                    'nivel': nivel,
                    'carrera': carrera,
                    'prerrequisitos': prerrequisitos_campo
                }

                if carrera and carrera.strip() and carrera.strip() != ',':
                    self.carreras.add(carrera)
                
                # Construir grafo solo con prerrequisitos de cursos (no créditos)
                for prereq in prereqs_lista:
                    # Ignorar si es un requisito de créditos
                    if not self._es_requisito_creditos(prereq):
                        prereq_key = (prereq, carrera)
                        self.grafo[prereq_key].append(clave)
    
    def _es_requisito_creditos(self, texto):
        """Detecta si un texto es un requisito de créditos"""
        texto_lower = texto.lower()
        patrones = [
            r'\d+\s*credito',
            r'credito.*\d+',
            r'\d+\s*cr[eé]dito'
        ]
        for patron in patrones:
            if re.search(patron, texto_lower):
                return True
        return False
    
    def _extraer_creditos_requeridos(self, texto):
        """Extrae la cantidad de créditos requeridos de un texto"""
        match = re.search(r'(\d+)\s*cr[eé]dito', texto.lower())
        if match:
            return int(match.group(1))
        return 0
    
    def filtrar_por_carrera(self, carrera):
        """Filtra el grafo por carrera específica"""
        cursos_carrera = {clave: info for clave, info in self.cursos.items() 
                         if clave[1] == carrera}
        
        grafo_carrera = defaultdict(list)
        for clave in cursos_carrera:
            grafo_carrera[clave] = []
        
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
        grado_entrada = {curso: 0 for curso in cursos_carrera}
        
        for curso in grafo_carrera:
            for vecino in grafo_carrera[curso]:
                grado_entrada[vecino] += 1
        
        for curso in cursos_carrera:
            prereqs = cursos_carrera[curso]['prerrequisitos']
            if prereqs.lower() == 'ninguno' and curso not in grado_entrada:
                grado_entrada[curso] = 0
        
        cola = deque([curso for curso, grado in grado_entrada.items() if grado == 0])
        orden = []
        
        while cola:
            nodo = cola.popleft()
            orden.append(nodo[0] if isinstance(nodo, tuple) else nodo)
            
            if nodo in grafo_carrera:
                for vecino in grafo_carrera[nodo]:
                    grado_entrada[vecino] -= 1
                    if grado_entrada[vecino] == 0:
                        cola.append(vecino)
        
        return orden if len(orden) == len(cursos_carrera) else None

# Inicializar grafo
grafo_global = GrafoCurricular()
grafo_global.cargar_csv('DatabaseG9_vf.txt')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/grafo')
def grafo():
    carreras = list(grafo_global.carreras)
    return render_template('grafo.html', carreras=carreras)

@app.route('/api/grafo/<carrera>')
def api_grafo(carrera):
    cursos_carrera, grafo_carrera = grafo_global.filtrar_por_carrera(carrera)
    
    tiene_ciclos = grafo_global.detectar_ciclos(grafo_carrera)
    
    orden_topologico = None
    if not tiene_ciclos:
        orden_topologico = grafo_global.ordenamiento_topologico(cursos_carrera, grafo_carrera)
    
    nodos = []
    for clave, info in cursos_carrera.items():
        curso_nombre = clave[0]
        nodos.append({
            'id': curso_nombre,
            'label': curso_nombre,
            'nivel': info['nivel'],
            'carrera': info['carrera']
        })
    
    aristas = []
    for prereq_key, cursos_siguientes in grafo_carrera.items():
        prereq_nombre = prereq_key[0]
        for curso_key in cursos_siguientes:
            curso_nombre = curso_key[0]
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
    return render_template('desbloqueados.html')

@app.route('/api/carreras')
def api_carreras():
    carreras_validas = [c for c in grafo_global.carreras if c and c.strip() and c.strip() != ',']
    return jsonify({
        'carreras': sorted(carreras_validas)
    })

@app.route('/api/cursos/<carrera>')
def api_cursos_carrera(carrera):
    cursos_carrera, _ = grafo_global.filtrar_por_carrera(carrera)
    
    cursos_dict = {}
    for clave, info in cursos_carrera.items():
        curso_nombre = clave[0]
        cursos_dict[curso_nombre] = {
            'nivel': info['nivel'],
            'creditos': info['creditos']
        }
    
    return jsonify({
        'cursos': cursos_dict
    })

@app.route('/api/desbloqueados/<carrera>/<curso>')
def api_desbloqueados(carrera, curso):
    cursos_carrera, grafo_carrera = grafo_global.filtrar_por_carrera(carrera)
    
    curso_key = (curso, carrera)
    
    desbloqueados_por_nivel = {}
    total_desbloqueados = 0
    
    if curso_key in grafo_carrera:
        from collections import deque
        
        cola = deque([(curso_key, 0)])
        visitados = {curso_key}
        
        while cola:
            nodo_actual, nivel_actual = cola.popleft()
            
            if nodo_actual in grafo_carrera:
                for vecino_key in grafo_carrera[nodo_actual]:
                    if vecino_key not in visitados:
                        visitados.add(vecino_key)
                        
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
    try:
        cursos_carrera, _ = grafo_global.filtrar_por_carrera(carrera)

        curso_key = None
        info_curso = None

        for clave, info in cursos_carrera.items():
            if clave[0].lower() == curso.lower():
                curso_key = clave
                info_curso = info
                break

        if not curso_key:
            return jsonify({'error': 'Curso no encontrado en esta carrera'}), 404

        raw_str = info_curso['prerrequisitos'].strip()
        prerrequisitos_info = []

        if raw_str and raw_str.lower() != "ninguno":
            lista_prereqs = [p.strip() for p in raw_str.split(',') if p.strip()]

            for prereq_nombre in lista_prereqs:
                prereq_key = (prereq_nombre, carrera)
                
                datos_prereq = {
                    'curso': prereq_nombre,
                    'nivel': 'N/A'
                }

                if prereq_key in cursos_carrera:
                    datos_prereq['nivel'] = cursos_carrera[prereq_key]['nivel']
                
                prerrequisitos_info.append(datos_prereq)

        return jsonify({
            'curso': curso_key[0],
            'tiene_prerrequisitos': len(prerrequisitos_info) > 0,
            'prerrequisitos': prerrequisitos_info,
            'total': len(prerrequisitos_info),
            'nivel_curso': info_curso['nivel']
        })

    except Exception as e:
        print(f"Error en api_prerrequisitos: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recomendar/<carrera>', methods=['POST'])
def api_recomendar(carrera):
    """
    Recomendador inteligente mejorado con soporte de créditos.
    Usa Algoritmo de Kahn modificado + validación de créditos acumulados.
    """
    try:
        data = request.get_json()
        cursos_aprobados = set(data.get('cursos_aprobados', []))
        
        # Filtrar cursos por carrera
        cursos_carrera, grafo_carrera = grafo_global.filtrar_por_carrera(carrera)
        
        if not cursos_carrera:
            return jsonify({'error': 'No se encontraron cursos para esta carrera'}), 404
        
        # 1. CALCULAR CRÉDITOS ACUMULADOS
        creditos_acumulados = 0
        for curso_nombre in cursos_aprobados:
            curso_key = (curso_nombre, carrera)
            if curso_key in cursos_carrera:
                creditos_acumulados += cursos_carrera[curso_key]['creditos']
        
        # 2. APLICAR ALGORITMO DE KAHN MODIFICADO
        grado_entrada = {}
        
        # Inicializar grados para cursos NO aprobados
        for curso_key in cursos_carrera.keys():
            curso_nombre = curso_key[0]
            if curso_nombre not in cursos_aprobados:
                grado_entrada[curso_nombre] = 0
        
        # Calcular grados basados en prerrequisitos de CURSOS no aprobados
        for curso_key, info in cursos_carrera.items():
            curso_nombre = curso_key[0]
            
            if curso_nombre in cursos_aprobados:
                continue
            
            prereqs_str = info['prerrequisitos']
            if prereqs_str and prereqs_str.lower() != 'ninguno':
                prereq_list = [p.strip() for p in prereqs_str.split(',')]
                for prereq in prereq_list:
                    # Solo contar prerrequisitos de CURSOS (ignorar créditos aquí)
                    if not grafo_global._es_requisito_creditos(prereq):
                        if prereq not in cursos_aprobados:
                            prereq_key = (prereq, carrera)
                            if prereq_key in cursos_carrera:
                                grado_entrada[curso_nombre] += 1
        
        # 3. IDENTIFICAR CURSOS CON GRADO 0 (Candidatos)
        candidatos = [curso for curso, grado in grado_entrada.items() if grado == 0]
        
        # 4. FILTRAR POR REQUISITOS DE CRÉDITOS
        cursos_disponibles = []
        cursos_bloqueados_por_creditos = []
        
        for curso_nombre in candidatos:
            curso_key = (curso_nombre, carrera)
            if curso_key not in cursos_carrera:
                continue
                
            info = cursos_carrera[curso_key]
            prereqs_str = info['prerrequisitos']
            
            # Verificar si tiene requisito de créditos
            creditos_necesarios = 0
            cumple_creditos = True
            
            if prereqs_str and prereqs_str.lower() != 'ninguno':
                prereq_list = [p.strip() for p in prereqs_str.split(',')]
                for prereq in prereq_list:
                    if grafo_global._es_requisito_creditos(prereq):
                        creditos_necesarios = grafo_global._extraer_creditos_requeridos(prereq)
                        if creditos_acumulados < creditos_necesarios:
                            cumple_creditos = False
                        break
            
            curso_info = {
                'curso': curso_nombre,
                'nivel': info['nivel'],
                'creditos': info['creditos'],
                'prerrequisitos': info['prerrequisitos'],
                'creditos_necesarios': creditos_necesarios
            }
            
            if cumple_creditos:
                cursos_disponibles.append(curso_info)
            else:
                curso_info['creditos_faltantes'] = creditos_necesarios - creditos_acumulados
                cursos_bloqueados_por_creditos.append(curso_info)
        
        # 5. AGRUPAR POR NIVEL
        por_nivel = {}
        for curso in cursos_disponibles:
            nivel = curso['nivel']
            if nivel not in por_nivel:
                por_nivel[nivel] = []
            por_nivel[nivel].append(curso)
        
        # 6. ESTADÍSTICAS
        total_cursos = len(cursos_carrera)
        cursos_completados = len(cursos_aprobados)
        progreso = (cursos_completados / total_cursos * 100) if total_cursos > 0 else 0
        
        # Calcular créditos totales de la carrera
        creditos_totales = sum(info['creditos'] for info in cursos_carrera.values())
        progreso_creditos = (creditos_acumulados / creditos_totales * 100) if creditos_totales > 0 else 0
        
        return jsonify({
            'cursos_disponibles': cursos_disponibles,
            'cursos_bloqueados_por_creditos': cursos_bloqueados_por_creditos,
            'por_nivel': por_nivel,
            'total_disponibles': len(cursos_disponibles),
            'total_bloqueados_por_creditos': len(cursos_bloqueados_por_creditos),
            'estadisticas': {
                'total_cursos': total_cursos,
                'cursos_aprobados': cursos_completados,
                'progreso': round(progreso, 1),
                'cursos_pendientes': total_cursos - cursos_completados,
                'creditos_acumulados': creditos_acumulados,
                'creditos_totales': creditos_totales,
                'progreso_creditos': round(progreso_creditos, 1)
            }
        })
    
    except Exception as e:
        print(f"Error en api_recomendar: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)