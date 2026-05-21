'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { WebSocketClient, WSMessage } from '@/lib/websocket';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from '@/components/ui/table';

import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';

// ── Types ──────────────────────────────────────────────────

interface FusionData {
  window_id: string;
  prediction: string;
  confidence_score: number;
  all_probabilities: Record<string, number>;
  dtw_distance: number;
  dtw_latency_ms: number;
  fusion_latency_ms: number;
  T_v: number;
  T_i: number;
  cost_matrix: number[][];
  bias_matrix: number[][];
  alignment_path: number[][];
  attention_weights: number[][];
}

interface SessionInfo {
  session_id: string;
  device_id: string;
  mode: string;
  state: string;
  imu_packet_count: number;
  frame_count: number;
  windows_processed: number;
}

interface StreamStats {
  imuCount: number;
  frameCount: number;
  imuRate: number;
  frameRate: number;
}

// ── Custom Hook ────────────────────────────────────────────

function useETASync(backendUrl: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [streamStats, setStreamStats] = useState<StreamStats>({
    imuCount: 0, frameCount: 0, imuRate: 0, frameRate: 0,
  });
  const [latestFusion, setLatestFusion] = useState<FusionData | null>(null);
  const [fusionHistory, setFusionHistory] = useState<FusionData[]>([]);
  const [latencyHistory, setLatencyHistory] = useState<{ ts: number; dtw: number; fusion: number }[]>([]);
  const [confidenceHistory, setConfidenceHistory] = useState<{ ts: number; confidence: number; prediction: string }[]>([]);

  const wsRef = useRef<WebSocketClient | null>(null);
  const imuTimestampsRef = useRef<number[]>([]);
  const frameTimestampsRef = useRef<number[]>([]);

  useEffect(() => {
    if (!backendUrl) return;
    const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws/diagnostics';
    const client = new WebSocketClient(wsUrl);
    wsRef.current = client;

    client.on('CONNECTED', (msg) => {
      setIsConnected(true);
      if (msg.data?.sessions) setSessions(msg.data.sessions as SessionInfo[]);
    });

    client.on('STATUS', (msg) => {
      if (msg.data?.sessions) setSessions(msg.data.sessions as SessionInfo[]);
    });

    client.on('PACKET_RECEIVED', (msg) => {
      const data = msg.data as { sensor: string; imu_count: number; frame_count: number };
      const now = Date.now();
      if (data.sensor === 'imu') imuTimestampsRef.current.push(now);
      else frameTimestampsRef.current.push(now);

      const cutoff = now - 2000;
      imuTimestampsRef.current = imuTimestampsRef.current.filter(t => t > cutoff);
      frameTimestampsRef.current = frameTimestampsRef.current.filter(t => t > cutoff);

      setStreamStats({
        imuCount: data.imu_count,
        frameCount: data.frame_count,
        imuRate: imuTimestampsRef.current.length / 2,
        frameRate: frameTimestampsRef.current.length / 2,
      });
    });

    client.on('FUSION_COMPLETED', (msg) => {
      const fusion = msg.data as unknown as FusionData;
      setLatestFusion(fusion);
      setFusionHistory(prev => [...prev.slice(-49), fusion]);
      setLatencyHistory(prev => [
        ...prev.slice(-99),
        { ts: msg.timestamp, dtw: fusion.dtw_latency_ms, fusion: fusion.fusion_latency_ms },
      ]);
      setConfidenceHistory(prev => [
        ...prev.slice(-99),
        { ts: msg.timestamp, confidence: fusion.confidence_score, prediction: fusion.prediction },
      ]);
    });

    client.connect();
    return () => { client.disconnect(); };
  }, [backendUrl]);

  return {
    isConnected, sessions, streamStats,
    latestFusion, fusionHistory, latencyHistory, confidenceHistory,
  };
}

// ── Custom Visualization Components ────────────────────────

function HeatmapCanvas({ matrix, title, width = 280, height = 200, path }: {
  matrix: number[][]; title: string; width?: number; height?: number; path?: number[][];
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !matrix || matrix.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rows = matrix.length;
    const cols = matrix[0].length;
    canvas.width = width;
    canvas.height = height;
    const cellW = width / cols;
    const cellH = height / rows;

    let min = Infinity, max = -Infinity;
    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        if (matrix[i][j] < min) min = matrix[i][j];
        if (matrix[i][j] > max) max = matrix[i][j];
      }
    }
    const range = max - min || 1;

    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        const val = (matrix[i][j] - min) / range;
        const r = Math.round(68 + val * 187);
        const g = Math.round(1 + val * 180 + (1 - val) * 80);
        const b = Math.round(84 + (1 - val) * 150 - val * 40);
        ctx.fillStyle = `rgb(${Math.min(255, r)},${Math.min(255, g)},${Math.max(0, b)})`;
        ctx.fillRect(j * cellW, i * cellH, cellW + 1, cellH + 1);
      }
    }

    if (path && path.length > 0) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(path[0][1] * cellW + cellW / 2, path[0][0] * cellH + cellH / 2);
      for (let k = 1; k < path.length; k++) {
        ctx.lineTo(path[k][1] * cellW + cellW / 2, path[k][0] * cellH + cellH / 2);
      }
      ctx.stroke();
    }
  }, [matrix, width, height, path]);

  return (
    <div className="flex flex-col items-center">
      <div className="text-xs font-medium text-muted-foreground mb-2">{title}</div>
      <canvas
        ref={canvasRef}
        className="rounded-lg ring-1 ring-border"
        style={{ width, height }}
      />
      <div className="flex items-center gap-2 mt-2 text-[10px] text-muted-foreground">
        <span>Low</span>
        <div className="w-16 h-2 rounded-full bg-gradient-to-r from-[#440154] via-[#21918c] to-[#fde725]" />
        <span>High</span>
      </div>
    </div>
  );
}

function ProbabilityBars({ probabilities }: { probabilities: Record<string, number> }) {
  const sorted = Object.entries(probabilities).sort(([, a], [, b]) => b - a);

  return (
    <div className="space-y-2">
      {sorted.map(([label, prob], i) => (
        <div key={label} className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-16 truncate capitalize">{label}</span>
          <div className="flex-1 h-2 rounded-full bg-secondary/30 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-accent transition-all duration-500"
              style={{ width: `${(prob * 100).toFixed(1)}%` }}
            />
          </div>
          <span className="text-xs font-mono text-foreground w-12 text-right">
            {(prob * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Main Dashboard Page ────────────────────────────────────

export default function DashboardPage() {
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');
  const [isConfigured, setIsConfigured] = useState(false);
  const [inputUrl, setInputUrl] = useState('http://localhost:8000');

  const {
    isConnected, sessions, streamStats,
    latestFusion, fusionHistory, latencyHistory, confidenceHistory,
  } = useETASync(isConfigured ? backendUrl : '');

  useEffect(() => { setIsConfigured(true); }, []);

  return (
    <div className="min-h-screen bg-background text-foreground dark">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center text-xs font-bold text-primary-foreground">
                η
              </div>
              <h1 className="text-lg font-semibold tracking-tight">
                ETA-Sync <span className="text-muted-foreground font-normal">Dashboard</span>
              </h1>
            </div>
            <Badge variant={isConnected ? 'default' : 'destructive'} className="gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-primary animate-pulse' : 'bg-destructive'}`} />
              {isConnected ? 'Live' : 'Disconnected'}
            </Badge>
          </div>

          <div className="flex items-center gap-3">
            <Input
              type="text"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              className="w-64 text-sm"
              placeholder="Backend URL"
            />
            <Button
              onClick={() => { setBackendUrl(inputUrl); setIsConfigured(true); }}
              variant="default"
              size="sm"
            >
              Connect
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-6 py-6">
        {/* ── Top Metrics Row ─────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          {[
            { label: 'IMU Packets', value: streamStats.imuCount, sub: `${streamStats.imuRate.toFixed(0)} Hz` },
            { label: 'Camera Frames', value: streamStats.frameCount, sub: `${streamStats.frameRate.toFixed(1)} FPS` },
            { label: 'Prediction', value: latestFusion?.prediction || '—', sub: latestFusion ? `Window ${latestFusion.window_id}` : 'Waiting...' },
            { label: 'Confidence', value: latestFusion ? `${(latestFusion.confidence_score * 100).toFixed(1)}%` : '—', sub: 'Score' },
            { label: 'DTW Latency', value: latestFusion ? `${latestFusion.dtw_latency_ms.toFixed(1)}` : '—', sub: 'ms' },
            { label: 'Fusion Latency', value: latestFusion ? `${latestFusion.fusion_latency_ms.toFixed(1)}` : '—', sub: 'ms' },
          ].map((m) => (
            <Card key={m.label} className="border">
              <CardContent className="p-4">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-widest mb-1">{m.label}</div>
                <div className="text-2xl font-bold tabular-nums text-primary">{m.value}</div>
                {m.sub && <div className="text-xs text-muted-foreground mt-1">{m.sub}</div>}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* ── Main Dashboard Grid ─────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* DTW Cost Matrix */}
          <Card className="border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">DTW Cost Matrix</CardTitle>
            </CardHeader>
            <CardContent>
              {latestFusion?.cost_matrix ? (
                <>
                  <HeatmapCanvas
                    matrix={latestFusion.cost_matrix}
                    title={`${latestFusion.T_v} × ${latestFusion.T_i}`}
                    path={latestFusion.alignment_path}
                    width={320} height={220}
                  />
                  <div className="mt-3 text-xs text-muted-foreground text-center">
                    DTW Distance: <span className="text-primary font-mono font-semibold">{latestFusion.dtw_distance.toFixed(4)}</span>
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center h-52 text-sm text-muted-foreground">
                  Waiting for alignment data...
                </div>
              )}
            </CardContent>
          </Card>

          {/* Attention Weights */}
          <Card className="border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Attention Weights</CardTitle>
            </CardHeader>
            <CardContent>
              {latestFusion?.attention_weights ? (
                <HeatmapCanvas
                  matrix={latestFusion.attention_weights}
                  title="Cross-Modal Attention"
                  width={320} height={220}
                />
              ) : (
                <div className="flex items-center justify-center h-52 text-sm text-muted-foreground">
                  Waiting for fusion data...
                </div>
              )}
            </CardContent>
          </Card>

          {/* DTW Bias Matrix */}
          <Card className="border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">DTW Bias Matrix</CardTitle>
            </CardHeader>
            <CardContent>
              {latestFusion?.bias_matrix ? (
                <HeatmapCanvas
                  matrix={latestFusion.bias_matrix}
                  title="Temporal Alignment Prior"
                  width={320} height={220}
                />
              ) : (
                <div className="flex items-center justify-center h-52 text-sm text-muted-foreground">
                  Waiting for alignment data...
                </div>
              )}
            </CardContent>
          </Card>

          {/* Activity Classification */}
          <Card className="border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Activity Classification</CardTitle>
            </CardHeader>
            <CardContent>
              {latestFusion?.all_probabilities ? (
                <div>
                  <div className="text-center mb-4">
                    <div className="text-3xl font-bold capitalize text-primary">
                      {latestFusion.prediction}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      Confidence: {(latestFusion.confidence_score * 100).toFixed(1)}%
                    </div>
                  </div>
                  <ProbabilityBars probabilities={latestFusion.all_probabilities} />
                </div>
              ) : (
                <div className="flex items-center justify-center h-52 text-sm text-muted-foreground">
                  Waiting for predictions...
                </div>
              )}
            </CardContent>
          </Card>

          {/* Latency Timeline — Recharts */}
          <Card className="border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Processing Latency</CardTitle>
            </CardHeader>
            <CardContent>
              {latencyHistory.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={140}>
                    <LineChart data={latencyHistory.map((d, i) => ({ idx: i, ...d }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="idx" hide />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} tickFormatter={(v) => `${v}ms`} />
                      <Tooltip
                        contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                        labelStyle={{ color: 'hsl(var(--foreground))' }}
                        formatter={(value) => [`${Number(value).toFixed(1)}ms`]}
                      />
                      <Line type="monotone" dataKey="dtw" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} name="DTW" />
                      <Line type="monotone" dataKey="fusion" stroke="hsl(var(--secondary))" strokeWidth={2} dot={false} name="Fusion" />
                      <Legend iconSize={8} wrapperStyle={{ fontSize: 10, paddingTop: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                    <span>Avg DTW: <span className="text-primary font-mono font-semibold">
                      {(latencyHistory.reduce((s, d) => s + d.dtw, 0) / latencyHistory.length).toFixed(1)}ms
                    </span></span>
                    <span>Avg Fusion: <span className="text-secondary font-mono font-semibold">
                      {(latencyHistory.reduce((s, d) => s + d.fusion, 0) / latencyHistory.length).toFixed(1)}ms
                    </span></span>
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center h-36 text-sm text-muted-foreground">
                  Waiting for data...
                </div>
              )}
            </CardContent>
          </Card>

          {/* Confidence Timeline — Recharts */}
          <Card className="border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Confidence Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              {confidenceHistory.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={140}>
                    <AreaChart data={confidenceHistory.map((d, i) => ({ idx: i, ...d }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="idx" hide />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                      <Tooltip
                        contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                        formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`]}
                      />
                      <defs>
                        <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.05} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="confidence" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#confGrad)" name="Confidence" />
                    </AreaChart>
                  </ResponsiveContainer>
                  <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                    <span>Latest: <span className="text-primary font-mono font-semibold">
                      {(confidenceHistory[confidenceHistory.length - 1].confidence * 100).toFixed(1)}%
                    </span></span>
                    <span>Windows: <span className="font-mono font-semibold">
                      {fusionHistory.length}
                    </span></span>
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center h-36 text-sm text-muted-foreground">
                  Waiting for data...
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Session Table — shadcn/ui Table ──────────── */}
        {sessions.length > 0 && (
          <Card className="mt-6 bg-[#111827]/60 border-white/5 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                Active Sessions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/5">
                    <TableHead>Session ID</TableHead>
                    <TableHead>Device</TableHead>
                    <TableHead>Mode</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead className="text-right">IMU</TableHead>
                    <TableHead className="text-right">Frames</TableHead>
                    <TableHead className="text-right">Windows</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <TableRow key={s.session_id} className="border-white/5 hover:bg-white/5">
                      <TableCell className="font-mono text-cyan-400">{s.session_id}</TableCell>
                      <TableCell className="text-muted-foreground">{s.device_id}</TableCell>
                      <TableCell>
                        <Badge variant={s.mode === 'async' ? 'secondary' : 'outline'} className="text-xs">
                          {s.mode}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={s.state === 'streaming' ? 'default' : s.state === 'processing' ? 'secondary' : 'outline'}
                          className="text-xs"
                        >
                          {s.state}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">{s.imu_packet_count}</TableCell>
                      <TableCell className="text-right font-mono">{s.frame_count}</TableCell>
                      <TableCell className="text-right font-mono">{s.windows_processed}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <footer className="mt-8 pb-6 text-center text-xs text-muted-foreground">
          ETA-Sync Research Dashboard · DTW-Guided Cross-Attention Fusion · shadcn/ui + Recharts · v1.0.0
        </footer>
      </main>
    </div>
  );
}
