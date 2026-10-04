#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Media;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// Estudio estadístico de la anomalía de gap (Plastun, Sibande, Gupta y Wohar, 2019).
// No opera: analiza el histórico del gráfico, imprime el informe en la ventana
// NinjaScript Output y exporta un CSV por sesión a Documentos\NinjaTrader 8\.
//
// Uso: gráfico de minutos (5, 15 o 30 min) con plantilla de horario RTH
// (p. ej. "CME US Index Futures RTH" para ES/MES, "US Equities RTH" para SPY).

public enum GapStudyThresholdMode
{
	FijoPct,
	PercentilMovil
}

namespace NinjaTrader.NinjaScript.Indicators
{
	public class GapAnomalyStudy : Indicator
	{
		private class SessionRec
		{
			public DateTime Date;
			public double Open, High, Low, Close;
			public double PrevClose = double.NaN;
			public double GapPct = double.NaN;
			public double ThresholdPct = double.NaN;
			public int Type = 99;	// 1 gap alcista, -1 gap bajista, 0 normal, 99 sin clasificar
			public bool Complete;
		}

		private List<SessionRec> sessions;
		private List<double> absGapHistory;
		private SessionRec cur;
		private bool reported;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Estudio de la anomalía de gap (Plastun et al., 2019): rendimiento intradía tras gaps RTH.";
				Name = "GapAnomalyStudy";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = false;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				ThresholdMode = GapStudyThresholdMode.PercentilMovil;
				FixedThresholdPct = 0.34;
				PercentileLevel = 91.5;
				LookbackSessions = 252;
				StartDate = new DateTime(2019, 1, 1);
				EndDate = new DateTime(2099, 12, 31);
				CommissionRoundTrip = 4.0;
				SlippageTicksPerSide = 1;
				Contracts = 1;
				ExportCsv = true;
				DrawMarkers = true;
			}
			else if (State == State.DataLoaded)
			{
				sessions = new List<SessionRec>();
				absGapHistory = new List<double>();
				cur = null;
				reported = false;
			}
			else if (State == State.Transition)
			{
				if (!reported)
				{
					reported = true;
					RunReport();
				}
			}
		}

		protected override void OnBarUpdate()
		{
			if (BarsInProgress != 0)
				return;

			if (Bars.IsFirstBarOfSession)
			{
				SessionRec prev = cur;
				if (prev != null)
					sessions.Add(prev);

				cur = new SessionRec { Date = Time[0].Date, Open = Open[0], High = High[0], Low = Low[0], Close = Close[0] };

				if (prev != null && prev.Close > 0)
				{
					cur.PrevClose = prev.Close;
					cur.GapPct = (cur.Open / prev.Close - 1.0) * 100.0;
					// El umbral solo usa gaps anteriores: sin sesgo de anticipación.
					cur.ThresholdPct = CurrentThreshold();
					if (!double.IsNaN(cur.ThresholdPct))
						cur.Type = cur.GapPct >= cur.ThresholdPct ? 1 : (cur.GapPct <= -cur.ThresholdPct ? -1 : 0);
					absGapHistory.Add(Math.Abs(cur.GapPct));

					if (DrawMarkers && (cur.Type == 1 || cur.Type == -1) && CurrentBar > 0)
					{
						Draw.Line(this, "GapRef" + CurrentBar, false, 1, prev.Close, 0, prev.Close, Brushes.Gray, DashStyleHelper.Dot, 1);
						if (cur.Type == 1)
							Draw.ArrowUp(this, "GapUp" + CurrentBar, false, 0, Low[0] - 4 * TickSize, Brushes.LimeGreen);
						else
							Draw.ArrowDown(this, "GapDn" + CurrentBar, false, 0, High[0] + 4 * TickSize, Brushes.Red);
					}
				}
			}
			else if (cur == null)
			{
				return;
			}
			else
			{
				cur.High = Math.Max(cur.High, High[0]);
				cur.Low = Math.Min(cur.Low, Low[0]);
				cur.Close = Close[0];
			}

			cur.Complete = Bars.IsLastBarOfSession;
		}

		private double CurrentThreshold()
		{
			if (ThresholdMode == GapStudyThresholdMode.FijoPct)
				return FixedThresholdPct;
			if (absGapHistory.Count < LookbackSessions)
				return double.NaN;

			List<double> w = absGapHistory.GetRange(absGapHistory.Count - LookbackSessions, LookbackSessions);
			w.Sort();
			double pos = PercentileLevel / 100.0 * (w.Count - 1);
			int lo = (int)Math.Floor(pos);
			int hi = Math.Min(lo + 1, w.Count - 1);
			return w[lo] + (w[hi] - w[lo]) * (pos - lo);
		}

		private void RunReport()
		{
			List<SessionRec> s = new List<SessionRec>(sessions);
			if (cur != null && cur.Complete)
				s.Add(cur);
			int n = s.Count;

			double pv = Instrument.MasterInstrument.PointValue;
			double tick = Instrument.MasterInstrument.TickSize;
			// Coste por operación expresado en puntos: deslizamiento entrada + salida y comisión.
			double costPts = 2.0 * SlippageTicksPerSide * tick + (pv > 0 ? CommissionRoundTrip / pv : 0);

			List<double> normal = new List<double>(), up = new List<double>(), dn = new List<double>();
			List<double> nextUp = new List<double>(), nextDn = new List<double>(), thresholds = new List<double>();
			int fillUpSame = 0, fillDnSame = 0, fillUp5 = 0, fillDn5 = 0, cntUp5 = 0, cntDn5 = 0;
			int trades = 0, wins = 0;
			double sumGrossPts = 0, totalNet = 0, grossWin = 0, grossLoss = 0, equity = 0, peak = 0, maxDD = 0;
			SortedDictionary<int, double[]> years = new SortedDictionary<int, double[]>();	// nUp, nDn, ganadoras, puntos brutos, neto $
			DateTime first = DateTime.MaxValue, last = DateTime.MinValue;

			StringBuilder csv = new StringBuilder();
			csv.AppendLine("Date,Open,High,Low,Close,PrevClose,GapPct,ThresholdPct,Type,RetPct,NextRetPct,FilledSameDay,Filled5d,GrossPts,NetUSD");

			for (int i = 0; i < n; i++)
			{
				SessionRec r = s[i];
				if (r.Type == 99 || r.Date < StartDate.Date || r.Date > EndDate.Date)
					continue;

				if (r.Date < first) first = r.Date;
				if (r.Date > last) last = r.Date;
				thresholds.Add(r.ThresholdPct);

				double ret = (r.Close / r.Open - 1.0) * 100.0;
				double nextRet = i + 1 < n ? (s[i + 1].Close / s[i + 1].Open - 1.0) * 100.0 : double.NaN;
				string fillSameStr = "", fill5Str = "";
				double grossPts = 0, net = 0;

				if (r.Type == 0)
				{
					normal.Add(ret);
				}
				else
				{
					bool isUp = r.Type == 1;
					(isUp ? up : dn).Add(ret);
					if (!double.IsNaN(nextRet))
						(isUp ? nextUp : nextDn).Add(nextRet);

					bool fillSame = isUp ? r.Low <= r.PrevClose : r.High >= r.PrevClose;
					if (fillSame) { if (isUp) fillUpSame++; else fillDnSame++; }
					fillSameStr = fillSame ? "1" : "0";

					if (i + 4 < n)
					{
						bool fill5 = false;
						for (int k = 0; k < 5 && !fill5; k++)
							fill5 = isUp ? s[i + k].Low <= r.PrevClose : s[i + k].High >= r.PrevClose;
						if (isUp) { cntUp5++; if (fill5) fillUp5++; }
						else { cntDn5++; if (fill5) fillDn5++; }
						fill5Str = fill5 ? "1" : "0";
					}

					// Regla del paper: entrar a favor del gap en la apertura y salir al cierre.
					grossPts = r.Type * (r.Close - r.Open);
					net = (grossPts - costPts) * pv * Contracts;
					trades++;
					if (net > 0) { wins++; grossWin += net; } else grossLoss -= net;
					sumGrossPts += grossPts;
					totalNet += net;
					equity += net;
					peak = Math.Max(peak, equity);
					maxDD = Math.Max(maxDD, peak - equity);

					int y = r.Date.Year;
					if (!years.ContainsKey(y)) years[y] = new double[5];
					years[y][isUp ? 0 : 1]++;
					if (net > 0) years[y][2]++;
					years[y][3] += grossPts;
					years[y][4] += net;
				}

				csv.AppendLine(string.Join(",", new string[] {
					r.Date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
					F(r.Open, 4), F(r.High, 4), F(r.Low, 4), F(r.Close, 4), F(r.PrevClose, 4),
					F(r.GapPct, 4), F(r.ThresholdPct, 4), r.Type.ToString(CultureInfo.InvariantCulture),
					F(ret, 4), double.IsNaN(nextRet) ? "" : F(nextRet, 4),
					fillSameStr, fill5Str, F(grossPts, 4), F(net, 2) }));
			}

			int valid = normal.Count + up.Count + dn.Count;
			Print("");
			Print("==================== ESTUDIO DE ANOMALÍA DE GAP ====================");
			Print("Referencia: Plastun, Sibande, Gupta y Wohar (2019)");
			Print("Instrumento: " + Instrument.FullName + " | Serie: " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType + " | Horario: " + Bars.TradingHours.Name);
			if (BarsPeriod.BarsPeriodType == BarsPeriodType.Day || BarsPeriod.BarsPeriodType == BarsPeriodType.Week || BarsPeriod.BarsPeriodType == BarsPeriodType.Month)
				Print("AVISO: use barras de minutos. Las barras diarias de futuros suelen incluir la sesión ETH y la apertura no es la de las 9:30 ET.");
			if (Bars.TradingHours.Name.IndexOf("RTH", StringComparison.OrdinalIgnoreCase) < 0)
				Print("AVISO: la plantilla de horario no parece RTH. El gap debe medirse entre el cierre y la apertura de la sesión regular.");
			if (valid == 0)
			{
				Print("Sin sesiones clasificadas. Cargue más historia (umbral móvil necesita " + LookbackSessions + " sesiones previas) o revise el rango de fechas.");
				return;
			}

			Print("Periodo analizado: " + first.ToString("yyyy-MM-dd") + " a " + last.ToString("yyyy-MM-dd") + " | Sesiones válidas: " + valid);
			Print("Umbral: " + (ThresholdMode == GapStudyThresholdMode.FijoPct
				? "fijo " + F(FixedThresholdPct, 2) + " %"
				: "percentil " + F(PercentileLevel, 1) + " de |gap| en " + LookbackSessions + " sesiones previas (medio " + F(thresholds.Average(), 3) + " %)"));

			Print("");
			Print("--- 1. Frecuencia ---");
			Print("Gaps alcistas: " + up.Count + " (" + F(100.0 * up.Count / valid, 1) + " %) | Gaps bajistas: " + dn.Count + " (" + F(100.0 * dn.Count / valid, 1) + " %)");

			Print("");
			Print("--- 2. Rendimiento intradía apertura->cierre (%) ---");
			Print("Grupo                    |    n | media %  | desv %  | % a favor | t vs normal | z acierto");
			PrintRow("Días normales", normal, normal, 1);
			PrintRow("Día de gap alcista", up, normal, 1);
			PrintRow("Día de gap bajista", dn, normal, -1);
			PrintRow("Día siguiente (alcista)", nextUp, normal, 1);
			PrintRow("Día siguiente (bajista)", nextDn, normal, -1);
			Print("% a favor = cierre en la dirección del gap. |t| o |z| > 1.96 => significativo al 5 %.");

			Print("");
			Print("--- 3. Relleno del gap ---");
			Print("Mismo día: alcistas " + Pct(fillUpSame, up.Count) + " | bajistas " + Pct(fillDnSame, dn.Count));
			Print("En 5 sesiones: alcistas " + Pct(fillUp5, cntUp5) + " | bajistas " + Pct(fillDn5, cntDn5) + "  (paper S&P 500: ~19-27 %)");

			Print("");
			Print("--- 4. Simulación: a favor del gap, apertura -> cierre ---");
			Print("Contratos: " + Contracts + " | Valor del punto: " + F(pv, 2) + " | Coste por operación: " + F(costPts, 4) + " pts (" + F(costPts * pv * Contracts, 2) + " $)");
			if (trades > 0)
			{
				double avgGross = sumGrossPts / trades;
				Print("Operaciones: " + trades + " | Ganadoras: " + Pct(wins, trades) + " | z acierto: " + F(BinomZ(wins, trades), 2));
				Print("Media bruta: " + F(avgGross, 3) + " pts | Ventaja/coste: " + (costPts > 0 ? F(avgGross / costPts, 2) : "n/d") + " (debe ser claramente > 1)");
				Print("Neto total: " + F(totalNet, 2) + " $ | Neto medio: " + F(totalNet / trades, 2) + " $ | Factor de beneficio: " + (grossLoss > 0 ? F(grossWin / grossLoss, 2) : "n/d") + " | Máx. drawdown: " + F(maxDD, 2) + " $");
			}

			Print("");
			Print("--- 5. Evolución por año (hipótesis H2) ---");
			Print("Año  | alc | baj | % ganad. | pts brutos | neto $");
			foreach (KeyValuePair<int, double[]> kv in years)
			{
				double[] v = kv.Value;
				int t = (int)(v[0] + v[1]);
				Print(kv.Key + " | " + ((int)v[0]).ToString().PadLeft(3) + " | " + ((int)v[1]).ToString().PadLeft(3) + " | "
					+ Pct((int)v[2], t).PadLeft(8) + " | " + F(v[3], 2).PadLeft(10) + " | " + F(v[4], 2).PadLeft(10));
			}

			if (ExportCsv)
			{
				try
				{
					string safe = new string(Instrument.FullName.Select(c => char.IsLetterOrDigit(c) ? c : '_').ToArray());
					string path = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "GapStudy_" + safe + ".csv");
					File.WriteAllText(path, csv.ToString());
					Print("");
					Print("CSV exportado: " + path);
				}
				catch (Exception ex)
				{
					Print("Error al exportar CSV: " + ex.Message);
				}
			}
			Print("=====================================================================");
		}

		private void PrintRow(string label, List<double> data, List<double> baseline, int dir)
		{
			if (data.Count == 0)
			{
				Print(label.PadRight(24) + " |    0 |");
				return;
			}
			int favor = data.Count(x => dir > 0 ? x > 0 : x < 0);
			string t = ReferenceEquals(data, baseline) ? "-" : F(WelchT(data, baseline), 2);
			Print(label.PadRight(24) + " | " + data.Count.ToString().PadLeft(4) + " | " + F(data.Average(), 3).PadLeft(8) + " | "
				+ F(StdDev(data), 3).PadLeft(7) + " | " + Pct(favor, data.Count).PadLeft(9) + " | " + t.PadLeft(11) + " | " + F(BinomZ(favor, data.Count), 2).PadLeft(9));
		}

		private static double StdDev(List<double> a)
		{
			if (a.Count < 2) return double.NaN;
			double m = a.Average();
			return Math.Sqrt(a.Sum(x => (x - m) * (x - m)) / (a.Count - 1));
		}

		private static double WelchT(List<double> a, List<double> b)
		{
			if (a.Count < 2 || b.Count < 2) return double.NaN;
			double sa = StdDev(a), sb = StdDev(b);
			return (a.Average() - b.Average()) / Math.Sqrt(sa * sa / a.Count + sb * sb / b.Count);
		}

		// z de proporción frente a 50 % (equivalente al z-test de la simulación del paper).
		private static double BinomZ(int k, int n)
		{
			return n == 0 ? double.NaN : ((double)k / n - 0.5) / Math.Sqrt(0.25 / n);
		}

		private static string Pct(int k, int n)
		{
			return n == 0 ? "n/d" : F(100.0 * k / n, 1) + " %";
		}

		private static string F(double v, int decimals)
		{
			return double.IsNaN(v) ? "" : v.ToString("F" + decimals, CultureInfo.InvariantCulture);
		}

		#region Properties
		[Display(Name = "Modo de umbral", Order = 1, GroupName = "1. Detección del gap")]
		public GapStudyThresholdMode ThresholdMode { get; set; }

		[Range(0.01, 20)]
		[Display(Name = "Umbral fijo (%)", Description = "Paper, S&P 500 2009-2018: 0.34 %", Order = 2, GroupName = "1. Detección del gap")]
		public double FixedThresholdPct { get; set; }

		[Range(50, 99.9)]
		[Display(Name = "Percentil (modo móvil)", Description = "91.5 => ~8.5 % de sesiones (~21 operaciones al año), como el paper en 2009-2018 (213 gaps en 10 años con umbral 0.34 %)", Order = 3, GroupName = "1. Detección del gap")]
		public double PercentileLevel { get; set; }

		[Range(20, 5000)]
		[Display(Name = "Sesiones de referencia", Order = 4, GroupName = "1. Detección del gap")]
		public int LookbackSessions { get; set; }

		[Display(Name = "Fecha inicio", Order = 1, GroupName = "2. Periodo")]
		public DateTime StartDate { get; set; }

		[Display(Name = "Fecha fin", Order = 2, GroupName = "2. Periodo")]
		public DateTime EndDate { get; set; }

		[Range(0, 1000)]
		[Display(Name = "Comisión ida y vuelta ($/contrato)", Order = 1, GroupName = "3. Costes")]
		public double CommissionRoundTrip { get; set; }

		[Range(0, 50)]
		[Display(Name = "Deslizamiento (ticks por lado)", Order = 2, GroupName = "3. Costes")]
		public int SlippageTicksPerSide { get; set; }

		[Range(1, 100000)]
		[Display(Name = "Contratos / acciones", Order = 3, GroupName = "3. Costes")]
		public int Contracts { get; set; }

		[Display(Name = "Exportar CSV", Order = 1, GroupName = "4. Salida")]
		public bool ExportCsv { get; set; }

		[Display(Name = "Marcar gaps en el gráfico", Order = 2, GroupName = "4. Salida")]
		public bool DrawMarkers { get; set; }
		#endregion
	}
}
