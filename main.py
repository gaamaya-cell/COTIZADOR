from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

app = FastAPI()

# ---------------------------------------------------------
# 1. CARGA DE BASE MAESTRA 
# ---------------------------------------------------------
try:
    
    BASE_PPR = pd.read_excel("PPR.xlsx")
    print("Base PPR cargada exitosamente.")
except Exception as e:
    BASE_PPR = pd.DataFrame()
    print(f"Error al cargar Base_PPR.xlsx: {e}")

# ---------------------------------------------------------
# 2. MODELOS DE DATOS 
# ---------------------------------------------------------
class Persona(BaseModel):
    Genero: str
    Edad: Union[int, str] # Acepta "25" o "1998-05-10"

class CotizacionInput(BaseModel):
    plan_destino: str
    poblacion: List[Persona]
    # Parámetros financieros (con valores por defecto si Salesforce no los envía)
    Gastos_sub: float = 0.15
    Gastos_vol: float = 0.15
    Comision_sub: float = 0.05
    Comision_vol: float = 0.05
    Margen_sub: float = 0.10
    Margen_vol: float = 0.10
    Recargo_Seguridad_sub: float = 0.0
    Recargo_Seguridad_vol: float = 0.0
    Recargo_Subsidio_sub: float = 0.0
    Recargo_Subsidio_vol: float = 0.0
    anexo1: float = 0.0
    anexo2: float = 0.0
    bolsa : float = 0.0
    medico_empresarial : float = 0.0
    vales_centros_medicos : float = 0.0
    consultas_domiciliarias : float = 0.0
    preexistencias : float = 0.0
    aic : float = 0.0
    gafas : float = 0.0
    vale_diferencial : float = 0.0
    v_anexonc : float = 0.0
    otros_dinero: float = 0.0
    otros_porc: float = 0.0



# ---------------------------------------------------------
# 3. FUNCIONES DE LÓGICA (Ajustadas para el contenedor)
# ---------------------------------------------------------

def limpiar_datos_basicos(df, col_genero="Genero", col_edad="Edad"):
    df = df.copy()
    if df.empty: return df

    def normalizar_genero(x):
        if pd.isna(x): return None
        x = str(x).strip().lower()
        if x in ["m", "masculino", "h", "hombre"]: return "H"
        if x in ["f", "femenino", "mujer"]: return "M"
        return None

    df["Genero_final"] = df[col_genero].apply(normalizar_genero)
    #hoy = pd.Timestamp.today()
    zona_co = pytz.timezone('America/Bogota')
    hoy = pd.Timestamp.now(tz=zona_co).replace(tzinfo=None)

    def calcular_edad(valor):
        if pd.isna(valor): return None
        try:
            if isinstance(valor, (int, float, str)) and str(valor).isdigit() and int(valor) < 120:
                return int(valor)
            fecha = pd.to_datetime(valor, errors="raise")
            return hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        except: return None

    df["Edad_final"] = df[col_edad].apply(calcular_edad)
    return df



# -------------------------
# CALCULAR TARIFAS (TODOS LOS PLANES MENOS DENTAL)
# -------------------------

def TF_GENERAL(
    df,
    PPR,
    Gastos_sub,
    Gastos_vol,
    Comision_sub,
    Comision_vol,
    Margen_sub,
    Margen_vol,
    Recargo_Seguridad_sub,
    Recargo_Seguridad_vol,
    Recargo_Subsidio_sub,
    Recargo_Subsidio_vol,
    PLAN,
    anexo1,
    anexo2,
    bolsa,
    medico_empresarial,
    vales_centros_medicos,
    consultas_domiciliarias,
    preexistencias,
    aic,
    gafas,
    vale_diferencial,
    v_anexonc,
    otros_dinero,
    otros_porc

):
    df = df.copy()


    # -------------------------
    # ARREGLAR EDAD Y GENERO
    # -------------------------

    df= limpiar_datos_basicos(df)

    # -------------------------
    # AGREGAR GRUPOS ETAREOS
    # -------------------------

    # Escenario 1


    # Definición de condiciones
    condiciones = [
        (df['Edad_final'] < 1),                                          # <1
        (df['Edad_final'] < 5),                                          # 1 a 4
        (df['Edad_final'] < 15),                                         # 5 a 14
        (df['Edad_final'] < 19) & (df['Genero_final'] == 'H'),           # 15 a 18 Hombre
        (df['Edad_final'] < 19) & (df['Genero_final'] == 'M'),           # 15 a 18 Mujer
        (df['Edad_final'] < 45) & (df['Genero_final'] == 'H'),           # 19 a 44 Hombre
        (df['Edad_final'] < 45) & (df['Genero_final'] == 'M'),           # 19 a 44 Mujer
        (df['Edad_final'] < 50),                                         # 45 a 49
        (df['Edad_final'] < 55),                                         # 50 a 54
        (df['Edad_final'] < 60),                                         # 55 a 59
        (df['Edad_final'] < 65),                                         # 60 a 64
        (df['Edad_final'] < 70),                                         # 65 a 69
        (df['Edad_final'] < 75)                                          # 70 a 74
    ]

    # Definición de etiquetas 
    opciones = [
        '<1', 
        '1_4', 
        '5_14', 
        '15_18H', 
        '15_18M', 
        '19_44H', 
        '19_44M', 
        '45_49', 
        '50_54', 
        '55_59', 
        '60_64', 
        '65_69', 
        '70_74'
    ]

    # Aplicación de la lógica
    
    df['GE'] = np.select(condiciones, opciones, default='75+')
        

    # -------------------------
    # BASE GE
    # -------------------------

    # Grupos etareos

    # General

    GE = pd.DataFrame({'GE' : ['<1', '1_4', '5_14', '15_18H', '15_18M', '19_44H', '19_44M', '45_49', '50_54', '55_59', '60_64', '65_69', '70_74', '75+']})

    GE['GE_FINAL'] = np.where(GE['GE'] == '65_69', 'De 65 a 69 años',
                            np.where(GE['GE'] == '70_74', 'De 70 a 74 años',
                                    np.where(GE['GE'] == '75+', 'Mayores a 74 años', 'Menores a 65 años')))
    
    # -------------------------
    # LOADINGS
    # -------------------------

    Sin_Sub = 1 - (Gastos_sub + Comision_sub + Margen_sub)
    Sin_Vol =  1 - (Gastos_vol + Comision_vol + Margen_vol)

    items = ['Gastos', 'Comisión', 'Margen', 'Recargo de seguridad', 'Recargo subsidio', 'Siniestralidad']
    subsidiada = [Gastos_sub, Comision_sub, Margen_sub, Recargo_Seguridad_sub, Recargo_Subsidio_sub, Sin_Sub]
    voluntaria = [Gastos_vol, Comision_vol, Margen_vol, Recargo_Seguridad_vol, Recargo_Subsidio_vol, Sin_Vol]

    Loadings = pd.DataFrame({'Items': items,
                            'Subsidiada' : subsidiada,
                            'Voluntaria': voluntaria})


    # -------------------------
    # CANTIDAD GE
    # -------------------------

    TF = (
        df['GE']
        .value_counts()
        .reset_index()
    )
    TF.columns = ['GE', 'Cantidad']
    

    # -------------------------
    # CRUCES
    # -------------------------

    TF_FINAL = GE.merge(TF, how= 'left', on = 'GE').fillna(0)
    TF_FINAL['PLAN'] = PLAN
    TF_PPR = TF_FINAL.merge(PPR[['PLAN','GE','PPR']], on = ['GE', 'PLAN'], how= 'left')
    TF_CONTEO = TF_PPR.iloc[:,0:3]
    TF_PPR['Tarifa Subsidiada'] = (TF_PPR['PPR'] * (1+Recargo_Seguridad_sub) * (1+Recargo_Subsidio_sub)) / Sin_Sub
    TF_PPR['Tarifa Voluntaria'] = (TF_PPR['PPR'] * (1+Recargo_Seguridad_vol) * (1+Recargo_Subsidio_vol)) / Sin_Vol
    TF_PPR['% Part'] = TF_PPR['Cantidad']/TF_PPR['Cantidad'].sum()

    # -------------------------
    # TARIFAS AGRUPADAS PREVIA
    # -------------------------

    
    suma_menores_65 = TF_PPR.loc[
        TF_PPR["GE_FINAL"] == "Menores a 65 años",
        "Cantidad"
    ].sum()

    if suma_menores_65 == 0: suma_menores_65 = 1

    TF_PPR["Tarifa Subsidiada Final"] = np.where(
        TF_PPR["GE_FINAL"] == "Menores a 65 años",
        TF_PPR["Tarifa Subsidiada"] * TF_PPR["Cantidad"] / suma_menores_65,
        TF_PPR["Tarifa Subsidiada"]
    )


    TF_PPR["Tarifa Voluntaria Final"] = np.where(
        TF_PPR["GE_FINAL"] == "Menores a 65 años",
        TF_PPR["Tarifa Voluntaria"] * TF_PPR["Cantidad"] / suma_menores_65,
        TF_PPR["Tarifa Voluntaria"]
    )




    # -------------------------
    # TARIFAS FINALES GE
    # -------------------------

    TF_GE = (
    TF_PPR.groupby(['PLAN','GE_FINAL'], as_index=False)[['Tarifa Subsidiada Final', 'Tarifa Voluntaria Final']]
      .sum()
      .rename(columns={
          'GE_FINAL': 'GE',
          'Tarifa Subsidiada Final': 'TARIFA_SUBSIDIADA',
          'Tarifa Voluntaria Final': 'TARIFA_VOLUNTARIA'

      })
    )

    orden_GE = [
    'Menores a 65 años',
    'De 65 a 69 años',
    'De 70 a 74 años',
    'Mayores a 74 años'
    ]

    TF_GE['GE'] = pd.Categorical(
        TF_GE['GE'],
        categories=orden_GE,
        ordered=True
    )

    TF_GE = TF_GE.sort_values('GE').reset_index(drop=True)

    # -------------------------
    # TARIFAS FINALES ANEXOS - ADICIONALES
    # -------------------------

    TF_GE_ANEXOS = TF_GE.copy()

    dinero = anexo1 + anexo2 + bolsa + medico_empresarial + aic + gafas + vale_diferencial + otros_dinero
    porcentaje = vales_centros_medicos + consultas_domiciliarias + preexistencias + otros_porc

    TF_GE_ANEXOS['TARIFA_SUBSIDIADA'] = (TF_GE_ANEXOS['TARIFA_SUBSIDIADA'] * (1+porcentaje)) + (dinero) 
    TF_GE_ANEXOS['TARIFA_VOLUNTARIA'] = (TF_GE_ANEXOS['TARIFA_VOLUNTARIA'] * (1+porcentaje)) + (dinero)

    # -------------------------
    # TARIFAS FINALES UNICAS 
    # -------------------------

    TF_UNICA = pd.DataFrame({'PLAN' : [PLAN],
        'TARIFA SUBSIDIADA' : (TF_PPR['Tarifa Subsidiada'] * TF_PPR['% Part']).sum(),
        'TARIFA VOLUNTARIA' : (TF_PPR['Tarifa Voluntaria'] * TF_PPR['% Part']).sum()}
        )
    
    return TF_GE_ANEXOS, TF_UNICA



# -------------------------
# CALCULAR TARIFAS PLAN DENTAL
# -------------------------

def TF_DENTAL(
    df,
    PPR,
    Gastos_sub,
    Gastos_vol,
    Comision_sub,
    Comision_vol,
    Margen_sub,
    Margen_vol,
    Recargo_Seguridad_sub,
    Recargo_Seguridad_vol,
    Recargo_Subsidio_sub,
    Recargo_Subsidio_vol,
    PLAN,
    anexo1,
    anexo2,
    bolsa,
    medico_empresarial,
    vales_centros_medicos,
    consultas_domiciliarias,
    preexistencias,
    aic,
    gafas,
    vale_diferencial,
    v_anexonc,
    otros_dinero,
    otros_porc

):
    df = df.copy()

    # -------------------------
    # ARREGLAR EDAD Y GENERO
    # -------------------------

    df = limpiar_datos_basicos(df)

    # -------------------------
    # AGREGAR GRUPOS ETAREOS
    # -------------------------

    # Escenario 1

    # Definición de condiciones
    condiciones = [
        (df['Edad_final'] < 1),                                          # <1
        (df['Edad_final'] < 5),                                          # 1 a 4
        (df['Edad_final'] < 15),                                         # 5 a 14
        (df['Edad_final'] < 19) & (df['Genero_final'] == 'H'),           # 15 a 18 Hombre
        (df['Edad_final'] < 19) & (df['Genero_final'] == 'M'),           # 15 a 18 Mujer
        (df['Edad_final'] < 45) & (df['Genero_final'] == 'H'),           # 19 a 44 Hombre
        (df['Edad_final'] < 45) & (df['Genero_final'] == 'M'),           # 19 a 44 Mujer
        (df['Edad_final'] < 50),                                         # 45 a 49
        (df['Edad_final'] < 55),                                         # 50 a 54
        (df['Edad_final'] < 60),                                         # 55 a 59
        (df['Edad_final'] < 65),                                         # 60 a 64
        (df['Edad_final'] < 70),                                         # 65 a 69
        (df['Edad_final'] < 75)                                          # 70 a 74
    ]

    # Definición de etiquetas 
    opciones = [
        '<1', 
        '1_4', 
        '5_14', 
        '15_18H', 
        '15_18M', 
        '19_44H', 
        '19_44M', 
        '45_49', 
        '50_54', 
        '55_59', 
        '60_64', 
        '65_69', 
        '70_74'
    ]

    # Aplicación de la lógica
  
    df['GE'] = np.select(condiciones, opciones, default='75+')
        
    # Grupos especificos del plan dental

    condiciones = [
        (df['Edad_final'] < 7),
        (df['Edad_final'] < 13),
        (df['Edad_final'] < 24),
        (df['Edad_final'] < 61)
    ]

    opciones = [
        'Menores de 7',
        'Desde 7 hasta 12',
        'Desde 13 hasta 23',
        'Desde 24 hasta 60'
    ]

    df['GE_DENTAL'] = np.select(condiciones, opciones, default =  'Mayores a 60')

    

    # -------------------------
    # PPR REHABILITACION ORAL
    # -------------------------

    RO = pd.DataFrame({'GE_DENTAL': ['Menores de 7', 'Desde 7 hasta 12', 'Desde 13 hasta 23', 'Desde 24 hasta 60', 'Mayores a 60'],
                   'PPR_RO': [16,98,1767,13737,31743]})
    
    # -------------------------
    # LOADINGS
    # -------------------------

    Sin_Sub = 1 - (Gastos_sub + Comision_sub + Margen_sub)
    Sin_Vol =  1 - (Gastos_vol + Comision_vol + Margen_vol)

    items = ['Gastos', 'Comisión', 'Margen', 'Recargo de seguridad', 'Recargo subsidio', 'Siniestralidad']
    subsidiada = [Gastos_sub, Comision_sub, Margen_sub, Recargo_Seguridad_sub, Recargo_Subsidio_sub, Sin_Sub]
    voluntaria = [Gastos_vol, Comision_vol, Margen_vol, Recargo_Seguridad_vol, Recargo_Subsidio_vol, Sin_Vol]

    Loadings = pd.DataFrame({'Items': items,
                            'Subsidiada' : subsidiada,
                            'Voluntaria': voluntaria})


    # -------------------------
    # CRUCES
    # -------------------------

    df['PLAN'] = PLAN
    DF_FINAL = df.merge(PPR, how='left', on = ['PLAN', 'GE'])
    DF_FINAL = DF_FINAL.merge(RO, how='left', on = 'GE_DENTAL')
    DF_FINAL['TARIFA DENTAL SUBSIDIADA'] = ((DF_FINAL['PPR'])*(1+Recargo_Seguridad_sub)*(1+Recargo_Subsidio_sub))/(Sin_Sub)
    DF_FINAL['TARIFA DENTAL + RO'] = ((DF_FINAL['PPR']+DF_FINAL['PPR_RO'])*(1+Recargo_Seguridad_sub)*(1+Recargo_Subsidio_sub))/(Sin_Sub)
    DF_FINAL['TARIFA DENTAL VOLUNTARIA'] = ((DF_FINAL['PPR'])*(1+Recargo_Seguridad_vol)*(1+Recargo_Subsidio_vol))/(Sin_Vol)

    # -------------------------
    # TARIFAS AGRUPADAS PREVIA
    # -------------------------

    RESUMEN =(
    DF_FINAL.groupby(['GE_DENTAL', 'PLAN'])
      .agg(
          Cantidad=('GE', 'count'),
          Tarifa_Subsidiada=('TARIFA DENTAL SUBSIDIADA', 'mean'),
          Tarifa_RO=('TARIFA DENTAL + RO', 'mean'),
          Tarifa_Voluntaria=('TARIFA DENTAL VOLUNTARIA', 'mean')
      )
      .reset_index()
    )
    RESUMEN['% Part'] = RESUMEN['Cantidad']/RESUMEN['Cantidad'].sum()
    RESUMEN['Tarifa_Subsidiada_ajustada'] = RESUMEN['Tarifa_Subsidiada']*RESUMEN['% Part']
    RESUMEN['Tarifa_RO_ajustada'] = RESUMEN['Tarifa_RO']*RESUMEN['% Part']
    RESUMEN['Tarifa_Voluntaria_ajustada'] = RESUMEN['Tarifa_Voluntaria']*RESUMEN['% Part']


    # -------------------------
    # TARIFAS FINALES GE
    # -------------------------
    TF_DENTAL_GE = RESUMEN[['PLAN','GE_DENTAL','Tarifa_Subsidiada','Tarifa_RO','Tarifa_Voluntaria']]
    TF_CONTEO = RESUMEN[['GE_DENTAL','Cantidad']]

    orden_GE = [
    'Menores de 7',
    'Desde 7 hasta 12',
    'Desde 13 hasta 23',
    'Desde 24 hasta 60',
    'Mayores a 60'
    ]

    TF_DENTAL_GE['GE_DENTAL'] = pd.Categorical(
        TF_DENTAL_GE['GE_DENTAL'],
        categories=orden_GE,
        ordered=True
    )

    TF_CONTEO['GE_DENTAL'] = pd.Categorical(
        TF_CONTEO['GE_DENTAL'],
        categories=orden_GE,
        ordered=True
    )

    TF_DENTAL_GE = TF_DENTAL_GE.sort_values('GE_DENTAL').reset_index(drop=True)
    TF_CONTEO = TF_CONTEO.sort_values('GE_DENTAL').reset_index(drop=True)

    # -------------------------
    # TARIFAS FINALES ANEXOS - ADICIONALES
    # -------------------------

    TF_DENTAL_GE_ANEXOS = TF_DENTAL_GE.copy()

    dinero = anexo1 + anexo2 + bolsa + medico_empresarial + aic + gafas + vale_diferencial + otros_dinero
    porcentaje = vales_centros_medicos + consultas_domiciliarias + preexistencias + otros_porc

    TF_DENTAL_GE_ANEXOS['Tarifa_Subsidiada'] = (TF_DENTAL_GE_ANEXOS['Tarifa_Subsidiada'] * (1+porcentaje)) + (dinero) 
    TF_DENTAL_GE_ANEXOS['Tarifa_RO'] = (TF_DENTAL_GE_ANEXOS['Tarifa_RO'] * (1+porcentaje)) + (dinero)
    TF_DENTAL_GE_ANEXOS['Tarifa_Voluntaria'] = (TF_DENTAL_GE_ANEXOS['Tarifa_Voluntaria'] * (1+porcentaje)) + (dinero)

    # -------------------------
    # TARIFAS FINALES UNICAS 
    # -------------------------

    TF_UNICA_DENTAL = (
    RESUMEN.groupby('PLAN')
        .agg(
            **{'TARIFA SUBSIDIADA': ('Tarifa_Subsidiada_ajustada', 'sum')},
            **{'TARIFA RO': ('Tarifa_RO_ajustada', 'sum')},
            **{'TARIFA VOLUNTARIA': ('Tarifa_Voluntaria_ajustada', 'sum')}
        )
        .reset_index()
    )   
    return TF_DENTAL_GE_ANEXOS, TF_UNICA_DENTAL



# ---------------------------------------------------------
# 4. EL ENDPOINT 
# ---------------------------------------------------------

@app.post("/cotizar")
async def ejecutar_cotizacion(input: CotizacionInput):
    # A. Convertir JSON a DataFrame
    df_raw = pd.DataFrame([p.dict() for p in input.poblacion])
    
    if df_raw.empty:
        return {"error": "La lista de población está vacía"}
    
    # B. Extraemos los parámetros financieros a un diccionario
    # Excluimos 'poblacion' porque esa ya la convertimos a DataFrame arriba
    parametros = input.dict(exclude={'poblacion', 'plan_destino'})


   # C. Ejecutar Lógica según el Plan
    try:
        plan_nombre = input.plan_destino.upper()
        
        if "DENTAL" in plan_nombre:
            # TF_DENTAL devuelve 5 cosas
            res_anexos, res_unica = TF_DENTAL(
                df=df_raw, PPR=BASE_PPR, PLAN=plan_nombre, **parametros
            )
        else:
            # TF_GENERAL también devuelve 5 cosas
            res_anexos, res_unica = TF_GENERAL(
                df=df_raw, PPR=BASE_PPR, PLAN=plan_nombre, **parametros
            )

        # D. Respuesta Final para Salesforce
        return {
            "status": "success",
            "plan_procesado": plan_nombre,
            "tarifa_unica_sub": float(res_unica['TARIFA SUBSIDIADA'].iloc[0]),
            "tarifa_unica_vol": float(res_unica['TARIFA VOLUNTARIA'].iloc[0]),
            "detalle_por_grupo": res_anexos.to_dict(orient="records")
            #"conteo_personas": res_conteo.to_dict(orient="records")
        }

    except Exception as e:
        return {"status": "error", "mensaje": f"Error en cálculo: {str(e)}"}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)