# GapAnomalyStudy (NinjaTrader 8)

Indicador de **análisis** que reproduce el estudio de Plastun et al. (2019) sobre los datos de tu gráfico. No envía órdenes.

## Instalación
1. Copia `GapAnomalyStudy.cs` en `Documentos\NinjaTrader 8\bin\Custom\Indicators\`.
2. En NinjaTrader abre *New > NinjaScript Editor* y compila con F5.

## Preparación del gráfico
| Parámetro | Valor recomendado |
|---|---|
| Instrumento | ES o MES (contrato continuo, *Merge back adjusted*) o SPY |
| Tipo de barra | Minuto, entre 5 y 30 (el resultado no depende del intervalo) |
| Trading hours | `CME US Index Futures RTH` (ES/MES) o `US Equities RTH` (SPY) |
| Carga de datos | Desde 2018-01-01, para tener 252 sesiones previas antes de 2019 |

Antes de empezar, descarga el histórico de minutos en *Tools > Historical Data*.

## Lectura de resultados
Los resultados aparecen en *New > NinjaScript Output*. El CSV por sesión se guarda en `Documentos\NinjaTrader 8\GapStudy_<instrumento>.csv`.

- **Sección 2:** si la anomalía sigue viva, el día de gap debe mostrar más del 50 % de cierres "a favor" y valores de t y z mayores que 1.96.
- **Sección 4:** la relación ventaja/coste tiene que ser claramente mayor que 1. De lo contrario, los costes se comen la ventaja.
- **Sección 5:** permite ver si el efecto se debilita año a año (hipótesis H2).

## Referencia
Plastun, A., Sibande, X., Gupta, R., & Wohar, M. E. (2019). *Price gap anomaly in the US stock market: The whole story* (Working Paper No. 2019-63). University of Pretoria. https://ssrn.com/abstract=3461283
