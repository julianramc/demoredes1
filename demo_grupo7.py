# -*- coding: utf-8 -*-
import streamlit as st
import cmath
import numpy as np
import pandas as pd
import time
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ==============================================================================
# DEMO ANALIZADOR DE LÍNEAS DE TRANSMISIÓN ELÉCTRICA - GRUPO 7 - MEJORADO
# Autor: Julián Oswaldo Ramírez Cabrera
# Institución Universitaria Pascual Bravo
# Mejoras implementadas: Validación de datos, contexto regulatorio, visualizaciones avanzadas
# ==============================================================================

# Constantes Físicas
SYSTEM_FREQUENCY = 60  # Hz, estándar en Colombia

class RegulatoryStandards:
    """Estándares regulatorios colombianos para líneas de transmisión"""
    
    # CREG 025 de 1995 - Regulación de voltaje
    VOLTAGE_REGULATION_LIMITS = {
        115: 5.0,   # kV: máximo 5%
        230: 3.0,   # kV: máximo 3%
        500: 2.0    # kV: máximo 2%
    }
    
    # Eficiencia mínima esperada
    MIN_EFFICIENCY = 90.0  # %
    
    # Factores de potencia típicos
    MIN_POWER_FACTOR = 0.85
    OPTIMAL_POWER_FACTOR = 0.95

def validate_input_data(voltage_kV, power_MVA, length_km, resistance_ohm, 
                       inductance_H, capacitance_uF, power_factor, radius_cm, DMG_cm):
    """Valida que los datos de entrada tengan sentido técnico"""
    errors = []
    warnings = []
    
    # Validaciones críticas
    if voltage_kV not in [115, 230, 500]:
        errors.append(f"⚠️ Voltaje {voltage_kV} kV no es estándar en Colombia (115, 230, 500 kV)")
    
    if power_MVA <= 0 or power_MVA > 2000:
        errors.append(f"⚠️ Potencia {power_MVA} MVA fuera del rango típico (1-2000 MVA)")
    
    if length_km <= 0 or length_km > 1000:
        errors.append(f"⚠️ Longitud {length_km} km fuera del rango típico (1-1000 km)")
    
    if resistance_ohm <= 0:
        errors.append("⚠️ La resistencia debe ser mayor a 0 Ω")
    
    if power_factor < 0.7 or power_factor > 1.0:
        errors.append(f"⚠️ Factor de potencia {power_factor} fuera del rango válido (0.7-1.0)")
    
    # Validaciones de advertencia
    if power_factor < RegulatoryStandards.MIN_POWER_FACTOR:
        warnings.append(f"⚡ Factor de potencia {power_factor:.2f} es bajo. Se recomienda > {RegulatoryStandards.MIN_POWER_FACTOR}")
    
    # Validar relación geométrica
    if DMG_cm <= radius_cm:
        errors.append("⚠️ La distancia media geométrica debe ser mayor al radio del conductor")
    
    # Validar densidad de corriente aproximada
    if voltage_kV > 0 and power_MVA > 0:
        current_density_approx = (power_MVA * 1000) / (np.sqrt(3) * voltage_kV * np.pi * (radius_cm/100)**2)
        if current_density_approx > 3e6:  # A/m²
            warnings.append(f"⚡ Densidad de corriente muy alta (~{current_density_approx/1e6:.1f} MA/m²)")
    
    return errors, warnings

def get_regulatory_context(regulation_percent, voltage_kV, efficiency_percent):
    """Proporciona contexto regulatorio para los resultados"""
    context = {}
    
    # Contexto de regulación de voltaje
    limit = RegulatoryStandards.VOLTAGE_REGULATION_LIMITS.get(voltage_kV, 5.0)
    if regulation_percent <= limit:
        context['regulation'] = {
            'status': '✅ Excelente',
            'message': f'Cumple con la Resolución CREG 025 de 1995 (≤{limit}% para {voltage_kV} kV)',
            'color': 'success'
        }
    elif regulation_percent <= limit * 1.2:
        context['regulation'] = {
            'status': '⚠️ Aceptable',
            'message': f'Cerca del límite CREG 025 de 1995 ({limit}% para {voltage_kV} kV)',
            'color': 'warning'
        }
    else:
        context['regulation'] = {
            'status': '❌ Deficiente',
            'message': f'Excede el límite CREG 025 de 1995 ({limit}% para {voltage_kV} kV)',
            'color': 'error'
        }
    
    # Contexto de eficiencia
    if efficiency_percent >= 95:
        context['efficiency'] = {
            'status': '✅ Excelente',
            'message': 'Eficiencia superior al 95%, óptima para transmisión',
            'color': 'success'
        }
    elif efficiency_percent >= RegulatoryStandards.MIN_EFFICIENCY:
        context['efficiency'] = {
            'status': '⚠️ Aceptable',
            'message': f'Eficiencia aceptable (≥{RegulatoryStandards.MIN_EFFICIENCY}%)',
            'color': 'warning'
        }
    else:
        context['efficiency'] = {
            'status': '❌ Deficiente',
            'message': f'Eficiencia por debajo del mínimo recomendado ({RegulatoryStandards.MIN_EFFICIENCY}%)',
            'color': 'error'
        }
    
    return context

class TransmissionLineAnalyzer:
    """Analizador de líneas de transmisión"""
    
    def __init__(self):
        self.results_history = []
    
    def calculate_power_losses(self, voltage_kV: float, power_MVA: float, resistance_ohm: float) -> dict:
        """Calcula las pérdidas de potencia con validación mejorada"""
        if voltage_kV <= 0:
            return {"current_A": 0, "losses_MW": 0, "efficiency_%": 0, "error": "Voltaje inválido"}
        
        try:
            current_A = (power_MVA * 1e6) / (np.sqrt(3) * voltage_kV * 1e3)
            losses_W = 3 * (current_A ** 2) * resistance_ohm
            losses_MW = losses_W / 1e6
            efficiency = ((power_MVA - losses_MW) / power_MVA) * 100 if power_MVA > 0 else 0
            
            return {
                "current_A": current_A,
                "losses_MW": losses_MW,
                "losses_W": losses_W,
                "efficiency_%": efficiency,
                "losses_percentage": (losses_MW / power_MVA) * 100 if power_MVA > 0 else 0,
                "current_density_A_per_mm2": current_A / (np.pi * (1.77)**2) if power_MVA > 0 else 0
            }
        except Exception as e:
            return {"error": f"Error en cálculo de pérdidas: {str(e)}"}
    
    def calculate_voltage_regulation(self, R_ohm: float, L_H: float, C_F: float, 
                                   length_km: float, V_R_kV: float, S_R_MVA: float, 
                                   pf_R: float, lagging: bool = True) -> dict:
        """Cálculo de la regulación de voltaje con validación mejorada"""
        try:
            w = 2 * np.pi * SYSTEM_FREQUENCY
            z = (R_ohm / length_km) + 1j * (w * L_H / length_km)
            y = 1j * (w * C_F / length_km)
            
            propagation_constant = cmath.sqrt(z * y)
            characteristic_impedance = cmath.sqrt(z / y)
            
            A = cmath.cosh(propagation_constant * length_km)
            B = characteristic_impedance * cmath.sinh(propagation_constant * length_km)
            
            V_R_phase = (V_R_kV * 1000) / np.sqrt(3)
            pf_angle = np.arccos(pf_R)
            if lagging: 
                pf_angle = -pf_angle
            
            I_R = (S_R_MVA * 1e6) / (np.sqrt(3) * V_R_kV * 1000)
            I_R_phasor = cmath.rect(I_R, pf_angle)
            
            V_S_phasor_full_load = A * V_R_phase + B * I_R_phasor
            V_R_no_load = abs(V_S_phasor_full_load) / abs(A)
            V_R_full_load = abs(V_R_phase)
            
            if V_R_full_load == 0: 
                return {"regulation_%": float('inf'), "voltage_drop_kV": 0, "error": "Voltaje de recepción inválido"}
            
            regulation = ((V_R_no_load - V_R_full_load) / V_R_full_load) * 100
            voltage_drop = (V_R_no_load - V_R_full_load) * np.sqrt(3) / 1000
            
            return {
                "regulation_%": regulation,
                "voltage_drop_kV": voltage_drop,
                "sending_voltage_kV": abs(V_S_phasor_full_load) * np.sqrt(3) / 1000,
                "no_load_voltage_kV": V_R_no_load * np.sqrt(3) / 1000,
                "impedance_magnitude_ohm": abs(characteristic_impedance),
                "propagation_constant": abs(propagation_constant)
            }
        except Exception as e:
            return {"error": f"Error en cálculo de regulación: {str(e)}"}
    
    def verify_corona_effect(self, V_nominal_kV: float, conductor_radius_cm: float, 
                           DMG_cm: float, roughness_factor: float = 0.85, 
                           temp_C: float = 25.0, pressure_atm: float = 1.0) -> dict:
        """Análisis del efecto corona con validación mejorada"""
        try:
            pressure_cmHg = pressure_atm * 76
            delta = (3.92 * pressure_cmHg) / (273 + temp_C)
            
            Vd_kV_phase = (21.1 * roughness_factor * delta * conductor_radius_cm * np.log(DMG_cm / conductor_radius_cm))
            V_op_kV_phase = V_nominal_kV / np.sqrt(3)
            
            has_corona = V_op_kV_phase > Vd_kV_phase
            safety_margin = ((Vd_kV_phase - V_op_kV_phase) / V_op_kV_phase) * 100
            
            if safety_margin > 20:
                risk_level = "Riesgo Bajo"
                risk_color = "green"
                recommendation = "Operación segura sin riesgo de corona"
            elif safety_margin > 10:
                risk_level = "Riesgo Medio"
                risk_color = "orange"
                recommendation = "Monitorear condiciones atmosféricas"
            else:
                risk_level = "Riesgo Alto"
                risk_color = "red"
                recommendation = "Considerar rediseño o cambio de conductor"
            
            return {
                "operating_voltage_phase_kV": V_op_kV_phase,
                "critical_disruptive_voltage_kV": Vd_kV_phase,
                "air_density_delta": delta,
                "corona_probable": has_corona,
                "safety_margin_%": safety_margin,
                "risk_level": risk_level,
                "risk_color": risk_color,
                "recommendation": recommendation,
                "gradient_kV_per_cm": V_op_kV_phase / conductor_radius_cm
            }
        except Exception as e:
            return {"error": f"Error en análisis de corona: {str(e)}"}
    
    def generate_performance_analysis(self, line_params: dict, operating_conditions: dict, 
                                    environmental_conditions: dict) -> dict:
        """Genera un análisis de rendimiento completo"""
        R_ohm = line_params["resistance_total_ohm"]
        L_H = line_params["inductance_total_H"]
        C_F = line_params["capacitance_total_F"]
        length_km = line_params["length_km"]
        radius_cm = line_params["conductor_radius_cm"]
        DMG_cm = line_params["DMG_cm"]
        
        V_R_kV = operating_conditions["reception_voltage_kV"]
        S_R_MVA = operating_conditions["reception_power_MVA"]
        pf_R = operating_conditions["power_factor"]
        
        roughness_factor = environmental_conditions["roughness_factor"]
        temp_C = environmental_conditions["temperature_C"]
        pressure_atm = environmental_conditions["pressure_atm"]
        
        losses_analysis = self.calculate_power_losses(V_R_kV, S_R_MVA, R_ohm)
        regulation_analysis = self.calculate_voltage_regulation(
            R_ohm, L_H, C_F, length_km, V_R_kV, S_R_MVA, pf_R
        )
        corona_analysis = self.verify_corona_effect(
            V_R_kV, radius_cm, DMG_cm, roughness_factor, temp_C, pressure_atm
        )
        
        return {
            "losses": losses_analysis,
            "regulation": regulation_analysis,
            "corona": corona_analysis,
            "timestamp": time.time()
        }

def create_advanced_visualizations(analysis_results: dict, line_params: dict):
    """Crea visualizaciones avanzadas usando Plotly"""
    
    def create_phasor_diagram():
        regulation_data = analysis_results["regulation"]
        V_send = regulation_data["sending_voltage_kV"]
        V_recv = line_params.get("voltage_kV", 230)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[0, V_send * 0.8], y=[0, V_send * 0.6],
            mode='lines+markers+text', name='Voltaje Envío',
            line=dict(color='blue', width=4),
            text=['', f'V_s = {V_send:.1f} kV'], textposition='top right'
        ))
        
        fig.add_trace(go.Scatter(
            x=[0, V_recv * 0.9], y=[0, V_recv * 0.3],
            mode='lines+markers+text', name='Voltaje Recepción',
            line=dict(color='red', width=4),
            text=['', f'V_r = {V_recv:.1f} kV'], textposition='bottom right'
        ))
        
        fig.update_layout(
            title="Diagrama Fasorial Simplificado",
            xaxis_title="Componente Real (kV)", yaxis_title="Componente Imaginaria (kV)",
            showlegend=True, width=500, height=400
        )
        return fig
    
    def create_power_sensitivity_analysis():
        power_range = np.linspace(50, 1000, 20)
        losses_range = []
        efficiency_range = []
        
        base_voltage = line_params.get("voltage_kV", 230)
        base_resistance = line_params.get("resistance_total_ohm", 15)
        
        for power in power_range:
            current = (power * 1e6) / (np.sqrt(3) * base_voltage * 1e3)
            losses = 3 * (current ** 2) * base_resistance / 1e6
            efficiency = ((power - losses) / power) * 100
            losses_range.append(losses)
            efficiency_range.append(efficiency)
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Pérdidas vs Potencia Transmitida', 'Eficiencia vs Potencia Transmitida'),
            vertical_spacing=0.1
        )
        
        fig.add_trace(
            go.Scatter(x=power_range, y=losses_range, name='Pérdidas (MW)', line=dict(color='red', width=3)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=power_range, y=efficiency_range, name='Eficiencia (%)', line=dict(color='green', width=3)),
            row=2, col=1
        )
        
        fig.update_xaxes(title_text="Potencia Transmitida (MVA)", row=2, col=1)
        fig.update_yaxes(title_text="Pérdidas (MW)", row=1, col=1)
        fig.update_yaxes(title_text="Eficiencia (%)", row=2, col=1)
        fig.update_layout(height=600, title_text="Análisis de Sensibilidad del Sistema")
        return fig
    
    def create_voltage_profile():
        length = line_params.get("length_km", 200)
        positions = np.linspace(0, length, 50)
        V_send = analysis_results["regulation"]["sending_voltage_kV"]
        V_recv = line_params.get("voltage_kV", 230)
        
        voltage_profile = V_send - (V_send - V_recv) * (positions / length)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=positions, y=voltage_profile,
            mode='lines+markers', name='Perfil de Voltaje',
            line=dict(color='purple', width=3), fill='tonexty'
        ))
        
        fig.add_hline(y=V_send, line_dash="dash", line_color="blue", annotation_text=f"Voltaje Envío: {V_send:.1f} kV")
        fig.add_hline(y=V_recv, line_dash="dash", line_color="red", annotation_text=f"Voltaje Recepción: {V_recv:.1f} kV")
        
        fig.update_layout(
            title="Perfil de Voltaje a lo largo de la Línea",
            xaxis_title="Distancia desde el Envío (km)", yaxis_title="Voltaje (kV)",
            width=600, height=400
        )
        return fig
    
    return create_phasor_diagram(), create_power_sensitivity_analysis(), create_voltage_profile()

def create_efficiency_gauge(efficiency_percent: float) -> str:
    """Crea un medidor de eficiencia basado en HTML"""
    if efficiency_percent >= 95: color = "#28a745"
    elif efficiency_percent >= 90: color = "#ffc107"
    else: color = "#dc3545"
    
    return f"""
    <div style="text-align: center; padding: 20px;">
        <div style="position: relative; width: 200px; height: 200px; margin: 0 auto;">
            <svg width="200" height="200" viewBox="0 0 200 200">
                <circle cx="100" cy="100" r="80" fill="none" stroke="#e0e0e0" stroke-width="20"/>
                <circle cx="100" cy="100" r="80" fill="none" stroke="{color}" stroke-width="20"
                        stroke-dasharray="{efficiency_percent * 5.03} 502.4" 
                        stroke-dashoffset="125.6" transform="rotate(-90 100 100)"/>
                <text x="100" y="100" text-anchor="middle" dy="0.3em" style="font-size: 24px; font-weight: bold; fill: {color};">
                    {efficiency_percent:.1f}%
                </text>
                <text x="100" y="130" text-anchor="middle" style="font-size: 14px; fill: #666;">
                    Eficiencia
                </text>
            </svg>
        </div>
    </div>
    """

def main():
    st.set_page_config(
        page_title="Analizador de Líneas de Transmisión",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = TransmissionLineAnalyzer()
    
    st.title("⚡ Analizador Avanzado de Líneas de Transmisión Eléctrica")
    st.markdown("""
    <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h3 style='color: white; margin: 0;'>🇨🇴 Cumplimiento Normativo CREG - Análisis Técnico Avanzado</h3>
        <p style='color: #e0e0e0; margin: 0.5rem 0 0 0;'>Evaluación integral con validación de datos, contexto regulatorio y visualizaciones interactivas</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("🔧 Configuración del Sistema")
        
        with st.expander("📏 Geometría de la Línea y Conductor", expanded=True):
            length_km = st.number_input("Longitud de la Línea (km)", 1.0, 1000.0, 180.0, 10.0, help="Longitud total en kilómetros")
            radius_cm = st.number_input("Radio del Conductor (cm)", 0.5, 10.0, 1.77, 0.1, help="Radio exterior del conductor")
            DMG_cm = st.number_input("Distancia Media Geométrica (cm)", 100.0, 2000.0, 700.0, 25.0, help="Entre conductores de fases")
        
        with st.expander("⚡ Parámetros Eléctricos", expanded=True):
            R_ohm = st.number_input("Resistencia Total por Fase (Ω)", 0.1, 100.0, 9.0, 0.5, help="Resistencia total de la línea")
            L_H = st.number_input("Inductancia Total por Fase (H)", 0.01, 2.0, 0.18, 0.01, "%.3f", help="Inductancia total de la línea")
            C_uF = st.number_input("Capacitancia Total Fase-Neutro (µF)", 0.1, 20.0, 2.15, 0.1, help="Capacitancia total fase-neutro")
        
        with st.expander("🔌 Condiciones de Operación", expanded=True):
            voltage_kV = st.selectbox("Voltaje Nominal (kV)", [115.0, 230.0, 500.0], index=1, help="Voltajes estándar en Colombia")
            power_MVA = st.slider("Potencia a Transmitir (MVA)", 50, 1000, 280, 10, help="Potencia aparente total")
            power_factor = st.slider("Factor de Potencia (en atraso)", 0.80, 1.0, 0.98, 0.01, help="Factor de potencia de la carga")
        
        with st.expander("🌡️ Condiciones Ambientales", expanded=True):
            temp_C = st.slider("Temperatura (°C)", -10, 50, 25, help="Temperatura ambiente")
            pressure_atm = st.slider("Presión Atmosférica (atm)", 0.70, 1.05, 1.0, help="Presión atmosférica (varía con altitud)")
            roughness_factor = st.slider("Factor de Rugosidad del Conductor", 0.70, 1.0, 0.85, help="0.7=rugoso, 1.0=liso")
    
    st.subheader("🔍 Validación de Datos de Entrada")
    errors, warnings = validate_input_data(voltage_kV, power_MVA, length_km, R_ohm, 
                                         L_H, C_uF, power_factor, radius_cm, DMG_cm)
    
    if errors:
        for error in errors: st.error(error)
        st.stop()
    if warnings:
        for warning in warnings: st.warning(warning)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Análisis en Tiempo Real")
        
        if st.button("🚀 Analizar Rendimiento de la Línea de Transmisión", type="primary"):
            line_params = {
                "resistance_total_ohm": R_ohm,
                "inductance_total_H": L_H,
                "capacitance_total_F": C_uF * 1e-6,
                "length_km": length_km,
                "conductor_radius_cm": radius_cm,
                "DMG_cm": DMG_cm,
                "voltage_kV": voltage_kV
            }
            operating_conditions = {
                "reception_voltage_kV": voltage_kV,
                "reception_power_MVA": power_MVA,
                "power_factor": power_factor
            }
            environmental_conditions = {
                "roughness_factor": roughness_factor,
                "temperature_C": temp_C,
                "pressure_atm": pressure_atm
            }
            
            with st.spinner('🔄 Realizando cálculos avanzados...'):
                time.sleep(1)
                results = st.session_state.analyzer.generate_performance_analysis(
                    line_params, operating_conditions, environmental_conditions
                )
                st.session_state.results = results
                st.session_state.line_params = line_params
        
        if 'results' in st.session_state:
            results = st.session_state.results
            
            if any('error' in section for section in results.values() if isinstance(section, dict)):
                st.error("❌ Error en los cálculos. Verifique los parámetros de entrada.")
                return
            
            reg_context = get_regulatory_context(
                results['regulation']['regulation_%'], 
                voltage_kV, 
                results['losses']['efficiency_%']
            )
            
            st.subheader("📈 Indicadores Clave de Rendimiento")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                eff_ctx = reg_context['efficiency']
                st.metric("Eficiencia del Sistema", f"{results['losses']['efficiency_%']:.2f}%", delta=f"-{results['losses']['losses_percentage']:.3f}% pérdidas")
                if eff_ctx['color'] == 'success': st.success(f"{eff_ctx['status']}: {eff_ctx['message']}")
                elif eff_ctx['color'] == 'warning': st.warning(f"{eff_ctx['status']}: {eff_ctx['message']}")
                else: st.error(f"{eff_ctx['status']}: {eff_ctx['message']}")
            
            with col_b:
                reg_ctx_data = reg_context['regulation']
                st.metric("Regulación de Voltaje", f"{results['regulation']['regulation_%']:.3f}%", delta="Menor es mejor")
                if reg_ctx_data['color'] == 'success': st.success(f"{reg_ctx_data['status']}: {reg_ctx_data['message']}")
                elif reg_ctx_data['color'] == 'warning': st.warning(f"{reg_ctx_data['status']}: {reg_ctx_data['message']}")
                else: st.error(f"{reg_ctx_data['status']}: {reg_ctx_data['message']}")
            
            with col_c:
                corona_data = results['corona']
                st.metric("Riesgo de Corona", corona_data['risk_level'], delta=f"{corona_data['safety_margin_%']:.1f}% margen")
                st.info(f"💡 {corona_data['recommendation']}")
    
    with col2:
        st.subheader("📊 Visualizaciones Avanzadas")
        
        if 'results' in st.session_state and 'line_params' in st.session_state:
            phasor_fig, sensitivity_fig, voltage_profile_fig = create_advanced_visualizations(
                st.session_state.results, st.session_state.line_params
            )
            
            viz_tab1, viz_tab2, viz_tab3 = st.tabs(["📐 Fasores", "📈 Sensibilidad", "📊 Perfil V"])
            
            with viz_tab1: st.plotly_chart(phasor_fig, use_container_width=True)
            with viz_tab2: st.plotly_chart(sensitivity_fig, use_container_width=True)
            with viz_tab3: st.plotly_chart(voltage_profile_fig, use_container_width=True)
            
        else:
            st.info("👆 Haz clic en 'Analizar' para generar las visualizaciones avanzadas")
    
    if 'results' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Reporte Técnico Detallado")
        
        results = st.session_state.results
        
        tab1, tab2, tab3, tab4 = st.tabs(["🔋 Análisis de Potencia", "📈 Análisis de Voltaje", "⚠️ Análisis de Corona", "📊 Resumen Ejecutivo"])
        
        with tab1:
            col_1, col_2 = st.columns(2)
            with col_1:
                st.write("**📊 Análisis Detallado de Pérdidas:**")
                losses_data = results['losses']
                st.write(f"• **Corriente de Línea:** {losses_data['current_A']:.2f} A")
                st.write(f"• **Pérdidas de Potencia:** {losses_data['losses_MW']:.4f} MW ({losses_data['losses_W']:.0f} W)")
                st.write(f"• **Porcentaje de Pérdidas:** {losses_data['losses_percentage']:.3f}%")
                st.write(f"• **Eficiencia del Sistema:** {losses_data['efficiency_%']:.3f}%")
                
                st.write("**🔍 Contexto Técnico:**")
                if losses_data['losses_percentage'] < 2: st.success("✅ Pérdidas muy bajas - Línea eficiente")
                elif losses_data['losses_percentage'] < 5: st.warning("⚠️ Pérdidas moderadas - Aceptable")
                else: st.error("❌ Pérdidas altas - Revisar diseño")
            
            with col_2:
                st.write("**⚡ Medidor de Eficiencia:**")
                gauge_html = create_efficiency_gauge(results['losses']['efficiency_%'])
                st.markdown(gauge_html, unsafe_allow_html=True)
        
        with tab2:
            regulation_data = results['regulation']
            st.write("**📈 Análisis Completo de Regulación:**")
            
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                st.write(f"• **Regulación de Voltaje:** {regulation_data['regulation_%']:.4f}%")
                st.write(f"• **Caída de Voltaje:** {regulation_data['voltage_drop_kV']:.3f} kV")
                st.write(f"• **Voltaje Extremo Emisor:** {regulation_data['sending_voltage_kV']:.2f} kV")
                st.write(f"• **Voltaje Sin Carga:** {regulation_data['no_load_voltage_kV']:.2f} kV")
            
            with col2_2:
                st.write(f"• **Impedancia Característica:** {regulation_data.get('impedance_magnitude_ohm', 'N/A'):.1f} Ω")
                st.write(f"• **Constante de Propagación:** {regulation_data.get('propagation_constant', 'N/A'):.6f}")
                
                limit = RegulatoryStandards.VOLTAGE_REGULATION_LIMITS.get(voltage_kV, 5.0)
                margin = regulation_data['regulation_%'] - limit
                st.metric(
                    label="Regulación vs Límite CREG",
                    value=f"{regulation_data['regulation_%']:.2f}%",
                    delta=f"{margin:+.2f}% vs Límite ({limit}%)",
                    delta_color="inverse"
                )
        
        with tab3:
            corona_data = results['corona']
            st.write("**⚠️ Análisis Detallado del Efecto Corona:**")
            
            col3_1, col3_2 = st.columns(2)
            with col3_1:
                st.write(f"• **Voltaje de Operación (fase):** {corona_data['operating_voltage_phase_kV']:.2f} kV")
                st.write(f"• **Voltaje Crítico Disruptivo:** {corona_data['critical_disruptive_voltage_kV']:.2f} kV")
                st.write(f"• **Margen de Seguridad:** {corona_data['safety_margin_%']:.2f}%")
                st.write(f"• **Densidad del Aire (δ):** {corona_data['air_density_delta']:.3f}")
            
            with col3_2:
                st.write(f"• **Gradiente Eléctrico:** {corona_data.get('gradient_kV_per_cm', 0):.2f} kV/cm")
                st.write(f"• **Recomendación:** {corona_data['recommendation']}")
                
                if corona_data['risk_level'] == "Riesgo Bajo": st.success(f"✅ {corona_data['risk_level']} - Operación segura")
                elif corona_data['risk_level'] == "Riesgo Medio": st.warning(f"⚠️ {corona_data['risk_level']} - Monitorear")
                else: st.error(f"❌ {corona_data['risk_level']} - Acción requerida")
        
        with tab4:
            st.write("**📊 Resumen Ejecutivo del Análisis:**")
            
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            
            with summary_col1:
                st.metric("Estado General", "✅ Operativo" if results['losses']['efficiency_%'] > 90 else "⚠️ Revisar")
                st.metric("Cumplimiento CREG", "✅ Cumple" if results['regulation']['regulation_%'] <= RegulatoryStandards.VOLTAGE_REGULATION_LIMITS.get(voltage_kV, 5.0) else "❌ No Cumple")
            
            with summary_col2:
                st.metric("Potencia Perdida", f"{results['losses']['losses_MW']:.3f} MW")
                st.metric("Costo Anual Pérdidas*", f"${results['losses']['losses_MW'] * 8760 * 50:.0f} USD")
                st.caption("*Estimado a $50/MWh")
            
            with summary_col3:
                st.metric("Capacidad Disponible", f"{power_MVA * results['losses']['efficiency_%'] / 100:.1f} MVA")
                st.metric("Factor de Utilización", f"{(power_MVA / 1000) * 100:.1f}%" if power_MVA < 1000 else "100%")

if __name__ == "__main__":
    main()

