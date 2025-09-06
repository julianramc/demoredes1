# -*- coding: utf-8 -*-
import streamlit as st
import cmath
import numpy as np
import pandas as pd
import time

# ==============================================================================
# DEMO ANALIZADOR DE LÍNEAS DE TRANSMISIÓN ELÉCTRICA - GRUPO 7
#Autor: Julián Oswaldo Ramírez cabrera
#Institutción Universitaria Pascual Bravo
# ==============================================================================

# Constantes Físicas
SYSTEM_FREQUENCY = 60  # Hz, estándar en Colombia

class TransmissionLineAnalyzer:
    """Demo Analizador de líneas de transmisión Julián Ramírez-Juan Tobón"""
    
    def __init__(self):
        self.results_history = []
    
    def calculate_power_losses(self, voltage_kV: float, power_MVA: float, resistance_ohm: float) -> dict:
        """Calcula las pérdidas de potencia """
        if voltage_kV <= 0:
            return {"current_A": 0, "losses_MW": 0, "efficiency_%": 0}
        
        current_A = (power_MVA * 1e6) / (np.sqrt(3) * voltage_kV * 1e3)
        losses_W = 3 * (current_A ** 2) * resistance_ohm
        losses_MW = losses_W / 1e6
        efficiency = ((power_MVA - losses_MW) / power_MVA) * 100 if power_MVA > 0 else 0
        
        return {
            "current_A": current_A,
            "losses_MW": losses_MW,
            "losses_W": losses_W,
            "efficiency_%": efficiency,
            "losses_percentage": (losses_MW / power_MVA) * 100 if power_MVA > 0 else 0
        }
    
    def calculate_voltage_regulation(self, R_ohm: float, L_H: float, C_F: float, 
                                   length_km: float, V_R_kV: float, S_R_MVA: float, 
                                   pf_R: float, lagging: bool = True) -> dict:
        """Cálculo de la regulación de voltaje"""
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
            return {"regulation_%": float('inf'), "voltage_drop_kV": 0}
        
        regulation = ((V_R_no_load - V_R_full_load) / V_R_full_load) * 100
        voltage_drop = (V_R_no_load - V_R_full_load) * np.sqrt(3) / 1000  # kV línea a línea
        
        return {
            "regulation_%": regulation,
            "voltage_drop_kV": voltage_drop,
            "sending_voltage_kV": abs(V_S_phasor_full_load) * np.sqrt(3) / 1000,
            "no_load_voltage_kV": V_R_no_load * np.sqrt(3) / 1000
        }
    
    def verify_corona_effect(self, V_nominal_kV: float, conductor_radius_cm: float, 
                           DMG_cm: float, roughness_factor: float = 0.85, 
                           temp_C: float = 25.0, pressure_atm: float = 1.0) -> dict:
        """Análisis del efecto corona"""
        pressure_cmHg = pressure_atm * 76
        delta = (3.92 * pressure_cmHg) / (273 + temp_C)
        
        Vd_kV_phase = (21.1 * roughness_factor * delta * conductor_radius_cm * np.log(DMG_cm / conductor_radius_cm))
        V_op_kV_phase = V_nominal_kV / np.sqrt(3)
        
        has_corona = V_op_kV_phase > Vd_kV_phase
        safety_margin = ((Vd_kV_phase - V_op_kV_phase) / V_op_kV_phase) * 100
        
        # Evaluación de riesgo
        if safety_margin > 20:
            risk_level = "Riesgo Bajo"
            risk_color = "green"
        elif safety_margin > 10:
            risk_level = "Riesgo Medio"
            risk_color = "orange"
        else:
            risk_level = "Riesgo Alto"
            risk_color = "red"
        
        return {
            "operating_voltage_phase_kV": V_op_kV_phase,
            "critical_disruptive_voltage_kV": Vd_kV_phase,
            "air_density_delta": delta,
            "corona_probable": has_corona,
            "safety_margin_%": safety_margin,
            "risk_level": risk_level,
            "risk_color": risk_color
        }
    
    def generate_performance_analysis(self, line_params: dict, operating_conditions: dict, 
                                    environmental_conditions: dict) -> dict:
        """Genera un análisis de rendimiento completo"""
        # Extraer parámetros
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
        
        # Realizar cálculos
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

def create_performance_charts(analysis_results: dict):
    """Crea gráficos usando componentes nativos de Streamlit"""
    
    # Datos del Gráfico de Distribución de Potencia
    losses_data = analysis_results["losses"]
    transmitted_power = 100 - losses_data["losses_percentage"]
    
    # Crear DataFrame para el gráfico de barras
    power_df = pd.DataFrame({
        'Componente': ['Potencia Transmitida', 'Pérdidas de Potencia'],
        'Porcentaje': [transmitted_power, losses_data["losses_percentage"]],
        'Color': ['#2E8B57', '#DC143C']
    })
    
    # Datos del Perfil de Voltaje
    regulation_data = analysis_results["regulation"]
    voltage_df = pd.DataFrame({
        'Ubicación': ['Extremo Emisor', 'Sin Carga', 'Plena Carga'],
        'Voltaje_kV': [
            regulation_data["sending_voltage_kV"],
            regulation_data["no_load_voltage_kV"],
            regulation_data["sending_voltage_kV"] - regulation_data["voltage_drop_kV"]
        ]
    })
    
    return power_df, voltage_df

def create_efficiency_gauge(efficiency_percent: float) -> str:
    """Crea un medidor de eficiencia basado en HTML"""
    # Determinar el color según la eficiencia
    if efficiency_percent >= 95:
        color = "#28a745"  # Verde
    elif efficiency_percent >= 90:
        color = "#ffc107"  # Amarillo
    else:
        color = "#dc3545"  # Rojo
    
    return f"""
    <div style="text-align: center; padding: 20px;">
        <div style="position: relative; width: 200px; height: 200px; margin: 0 auto;">
            <svg width="200" height="200" viewBox="0 0 200 200">
                <circle cx="100" cy="100" r="80" fill="none" stroke="#e0e0e0" stroke-width="20"/>
                <circle cx="100" cy="100" r="80" fill="none" stroke="{color}" stroke-width="20"
                        stroke-dasharray="{efficiency_percent * 5.03} 502.4" 
                        stroke-dashoffset="125.6" transform="rotate(-90 100 100)"/>
                <text x="100" y="100" text-anchor="middle" dy="0.3em" 
                      style="font-size: 24px; font-weight: bold; fill: {color};">
                    {efficiency_percent:.1f}%
                </text>
                <text x="100" y="130" text-anchor="middle" 
                      style="font-size: 14px; fill: #666;">
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
    
    # Inicializar analizador
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = TransmissionLineAnalyzer()
    
    # Encabezado
    st.title("⚡ Analizador de Rendimiento de Líneas de Transmisión Eléctrica")
    st.markdown("""
    <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h3 style='color: white; margin: 0;'>Herramienta de Análisis Avanzado para Sistemas de Transmisión Eléctrica</h3>
        <p style='color: #e0e0e0; margin: 0.5rem 0 0 0;'>Evaluación integral del rendimiento con cálculos en tiempo real y visualizaciones interactivas</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Configuración de la Barra Lateral
    with st.sidebar:
        st.header("🔧 Configuración del Sistema")
        
        # Parámetros de la Línea
        with st.expander("📏 Geometría de la Línea y Conductor", expanded=True):
            length_km = st.number_input("Longitud de la Línea (km)", min_value=1.0, value=200.0, step=10.0)
            radius_cm = st.number_input("Radio del Conductor (cm)", min_value=0.5, value=1.77, step=0.1)
            DMG_cm = st.number_input("Distancia Media Geométrica (cm)", min_value=100.0, value=750.0, step=25.0)
        
        # Parámetros Eléctricos
        with st.expander("⚡ Parámetros Eléctricos", expanded=True):
            R_ohm = st.number_input("Resistencia Total por Fase (Ω)", min_value=0.1, value=15.0, step=0.5)
            L_H = st.number_input("Inductancia Total por Fase (H)", min_value=0.01, value=0.35, step=0.01, format="%.3f")
            C_F = st.number_input("Capacitancia Total Fase-Neutro (µF)", min_value=0.1, value=2.5, step=0.1)
        
        # Condiciones de Operación
        with st.expander("🔌 Condiciones de Operación", expanded=True):
            voltage_kV = st.selectbox("Voltaje Nominal (kV)", [115.0, 230.0, 500.0], index=1)
            power_MVA = st.slider("Potencia a Transmitir (MVA)", 50, 1000, 300, 10)
            power_factor = st.slider("Factor de Potencia (en atraso)", 0.80, 1.0, 0.95, 0.01)
        
        # Condiciones Ambientales
        with st.expander("🌡️ Condiciones Ambientales", expanded=True):
            temp_C = st.slider("Temperatura (°C)", -10, 50, 20)
            pressure_atm = st.slider("Presión Atmosférica (atm)", 0.70, 1.05, 0.85)
            roughness_factor = st.slider("Factor de Rugosidad del Conductor", 0.70, 1.0, 0.82)
    
    # Área de Contenido Principal
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Análisis en Tiempo Real")
        
        if st.button("🚀 Analizar Rendimiento de la Línea de Transmisión", type="primary"):
            # Preparar parámetros
            line_params = {
                "resistance_total_ohm": R_ohm,
                "inductance_total_H": L_H,
                "capacitance_total_F": C_F * 1e-6,  # Convertir a Faradios
                "length_km": length_km,
                "conductor_radius_cm": radius_cm,
                "DMG_cm": DMG_cm
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
            
            # Realizar análisis
            with st.spinner('🔄 Realizando cálculos avanzados...'):
                time.sleep(1)  # Simular tiempo de procesamiento
                results = st.session_state.analyzer.generate_performance_analysis(
                    line_params, operating_conditions, environmental_conditions
                )
                st.session_state.results = results
        
        # Mostrar resultados si están disponibles
        if 'results' in st.session_state:
            results = st.session_state.results
            
            # Indicadores Clave
            st.subheader("📈 Indicadores Clave de Rendimiento")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric(
                    "Eficiencia", 
                    f"{results['losses']['efficiency_%']:.1f}%",
                    delta=f"-{results['losses']['losses_percentage']:.2f}% pérdidas"
                )
            
            with col_b:
                st.metric(
                    "Regulación de Voltaje", 
                    f"{results['regulation']['regulation_%']:.2f}%",
                    delta="Menor es mejor"
                )
            
            with col_c:
                corona_color = results['corona']['risk_color']
                st.metric(
                    "Riesgo de Corona", 
                    results['corona']['risk_level'],
                    delta=f"{results['corona']['safety_margin_%']:.1f}% de margen"
                )
    
    with col2:
        st.subheader("📊 Visualizaciones de Rendimiento")
        
        if 'results' in st.session_state:
            power_df, voltage_df = create_performance_charts(st.session_state.results)
            
            # Gráfico de Distribución de Potencia
            st.write("**Análisis de Distribución de Potencia**")
            st.bar_chart(power_df.set_index('Componente')['Porcentaje'])
            
            # Gráfico de Perfil de Voltaje
            st.write("**Perfil de Voltaje a lo largo de la Línea**")
            st.line_chart(voltage_df.set_index('Ubicación')['Voltaje_kV'])
            
        else:
            st.info("👆 Haz clic en 'Analizar' para generar las visualizaciones de rendimiento")
    
    # Sección de Resultados Detallados
    if 'results' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Reporte de Análisis Detallado")
        
        results = st.session_state.results
        
        # Crear pestañas para diferentes análisis
        tab1, tab2, tab3 = st.tabs(["🔋 Análisis de Potencia", "📈 Análisis de Voltaje", "⚠️ Análisis de Corona"])
        
        with tab1:
            col_1, col_2 = st.columns(2)
            with col_1:
                st.write("**Análisis de Pérdidas de Potencia:**")
                st.write(f"• Corriente de Línea: {results['losses']['current_A']:.2f} A")
                st.write(f"• Pérdidas de Potencia: {results['losses']['losses_MW']:.3f} MW")
                st.write(f"• Porcentaje de Pérdidas: {results['losses']['losses_percentage']:.2f}%")
                st.write(f"• Eficiencia del Sistema: {results['losses']['efficiency_%']:.2f}%")
            
            with col_2:
                st.write("**Medidor de Eficiencia del Sistema:**")
                gauge_html = create_efficiency_gauge(results['losses']['efficiency_%'])
                st.markdown(gauge_html, unsafe_allow_html=True)
        
        with tab2:
            st.write("**Análisis de Regulación de Voltaje:**")
            st.write(f"• Regulación de Voltaje: {results['regulation']['regulation_%']:.2f}%")
            st.write(f"• Caída de Voltaje: {results['regulation']['voltage_drop_kV']:.2f} kV")
            st.write(f"• Voltaje en el Extremo Emisor: {results['regulation']['sending_voltage_kV']:.2f} kV")
            
            # Evaluación de la regulación
            reg_value = results['regulation']['regulation_%']
            if reg_value < 3:
                st.success("✅ Regulación de voltaje excelente (< 3%)")
            elif reg_value < 5:
                st.warning("⚠️ Regulación de voltaje aceptable (3-5%)")
            else:
                st.error("❌ Regulación de voltaje deficiente (> 5%)")
        
        with tab3:
            corona_data = results['corona']
            st.write("**Análisis del Efecto Corona:**")
            st.write(f"• Voltaje de Operación (fase): {corona_data['operating_voltage_phase_kV']:.2f} kV")
            st.write(f"• Voltaje Crítico Disruptivo: {corona_data['critical_disruptive_voltage_kV']:.2f} kV")
            st.write(f"• Margen de Seguridad: {corona_data['safety_margin_%']:.2f}%")
            
            # Indicador de riesgo
            if corona_data['risk_level'] == "Riesgo Bajo":
                st.success(f"✅ {corona_data['risk_level']} - Efecto corona improbable")
            elif corona_data['risk_level'] == "Riesgo Medio":
                st.warning(f"⚠️ {corona_data['risk_level']} - Monitorear condiciones")
            else:
                st.error(f"❌ {corona_data['risk_level']} - Efecto corona probable")

if __name__ == "__main__":
    main()
# To run this app, use the command: streamlit run demo_grupo7.py