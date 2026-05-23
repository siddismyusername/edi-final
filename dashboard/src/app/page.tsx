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

  const [accelHistory, setAccelHistory] = useState<{ ts: string; x: number; y: number; z: number }[]>([]);
  const [gyroHistory, setGyroHistory] = useState<{ ts: string; x: number; y: number; z: number }[]>([]);
  const [latestFrame, setLatestFrame] = useState<string | null>(null);
  const [latestFrameId, setLatestFrameId] = useState<number | null>(null);
  const [latestFrameTime, setLatestFrameTime] = useState<number | null>(null);

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
      setAccelHistory([]);
      setGyroHistory([]);
      setLatestFrame(null);
      setLatestFrameId(null);
      setLatestFrameTime(null);
    });

    client.on('STATUS', (msg) => {
      if (msg.data?.sessions) setSessions(msg.data.sessions as SessionInfo[]);
    });

    client.on('PACKET_RECEIVED', (msg) => {
      const data = msg.data as any;
      const now = Date.now();
      if (data.sensor === 'imu') {
        imuTimestampsRef.current.push(now);
        
        // Format timestamp as a readable X-axis label (seconds.milliseconds)
        const tsLabel = new Date(data.timestamp * 1000).toLocaleTimeString([], {
          hour: '2-digit', minute: '2-digit', second: '2-digit',
          fractionalSecondDigits: 2
        } as any);

        const newAccel = {
          ts: tsLabel,
          x: data.ax,
          y: data.ay,
          z: data.az,
        };
        const newGyro = {
          ts: tsLabel,
          x: data.gx,
          y: data.gy,
          z: data.gz,
        };

        setAccelHistory(prev => [...prev.slice(-299), newAccel]);
        setGyroHistory(prev => [...prev.slice(-299), newGyro]);
      } else {
        frameTimestampsRef.current.push(now);
        if (data.data) {
          setLatestFrame(data.data);
          setLatestFrameId(data.frame_id);
          setLatestFrameTime(data.timestamp);
        }
      }

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
    accelHistory, gyroHistory, latestFrame, latestFrameId, latestFrameTime,
  };
}

// ── Custom Visualization Components ────────────────────────



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
  const [visiblePoints, setVisiblePoints] = useState<number>(150);

  const {
    isConnected, sessions, streamStats,
    latestFusion, fusionHistory, latencyHistory, confidenceHistory,
    accelHistory, gyroHistory, latestFrame, latestFrameId, latestFrameTime,
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
          {/* Real-time Camera Frame */}
          <Card className="border bg-card/60 backdrop-blur-md relative overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/30">
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <svg className="w-4 h-4 text-primary animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Real-Time Camera Frame
              </CardTitle>
              {latestFrame && (
                <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600 text-[10px] py-0.5 px-2 font-semibold tracking-wider animate-pulse flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
                  LIVE
                </Badge>
              )}
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center min-h-[260px] p-4 relative">
              {latestFrame ? (
                <div className="w-full relative rounded-lg overflow-hidden border border-border group">
                  <img
                    src={`data:image/jpeg;base64,${latestFrame}`}
                    alt="Live Frame"
                    className="w-full aspect-[4/3] object-cover rounded-lg transition-transform duration-500 group-hover:scale-[1.02]"
                  />
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 text-[11px] text-white font-mono flex items-center justify-between">
                    <span className="opacity-90">Frame ID: #{latestFrameId}</span>
                    {latestFrameTime && (
                      <span className="opacity-90">
                        {new Date(latestFrameTime * 1000).toLocaleTimeString([], {
                          hour: '2-digit', minute: '2-digit', second: '2-digit',
                          fractionalSecondDigits: 3
                        } as any)}
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6 bg-secondary/10 rounded-lg w-full aspect-[4/3] border border-dashed border-border group">
                  <div className="relative mb-3 flex items-center justify-center">
                    <div className="absolute inset-0 rounded-full bg-primary/10 w-12 h-12 animate-ping" />
                    <div className="relative rounded-full bg-primary/20 w-12 h-12 flex items-center justify-center text-primary transition-transform duration-300 group-hover:rotate-12">
                      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </div>
                  </div>
                  <span className="text-sm font-medium text-muted-foreground">Waiting for camera feed...</span>
                  <span className="text-[10px] text-muted-foreground/60 mt-1 max-w-[200px]">Ensure mobile app is streaming frames</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Live Accelerometer */}
          <Card className="border bg-card/60 backdrop-blur-md transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/30">
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <svg className="w-4 h-4 text-[#ec4899]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                Live Accelerometer (m/s²)
              </CardTitle>
              <div className="flex items-center gap-4">
                {accelHistory.length > 0 && (
                  <div className="flex gap-2 text-[10px] font-mono border-r border-border/60 pr-4">
                    <span className="text-[#ec4899]">X: {accelHistory[accelHistory.length - 1].x.toFixed(2)}</span>
                    <span className="text-[#3b82f6]">Y: {accelHistory[accelHistory.length - 1].y.toFixed(2)}</span>
                    <span className="text-[#10b981]">Z: {accelHistory[accelHistory.length - 1].z.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex items-center gap-1 bg-secondary/30 p-0.5 rounded-lg border border-border/40">
                  {([50, 150, 300] as const).map((pts) => (
                    <button
                      key={pts}
                      onClick={() => setVisiblePoints(pts)}
                      className={`px-1.5 py-0.5 rounded text-[9px] font-medium transition-all ${
                        visiblePoints === pts
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary/40'
                      }`}
                    >
                      {pts}p
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="min-h-[260px] p-4 flex flex-col justify-between">
              {accelHistory.length > 0 ? (
                <div className="w-full h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={accelHistory.slice(-visiblePoints)} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                      <XAxis dataKey="ts" stroke="hsl(var(--muted-foreground))" fontSize={9} tickLine={false} axisLine={false} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={9} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                      <Tooltip
                        contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 11 }}
                        labelStyle={{ color: 'hsl(var(--foreground))' }}
                      />
                      <Line type="linear" dataKey="x" stroke="#ec4899" strokeWidth={1.5} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} name="X-axis" />
                      <Line type="linear" dataKey="y" stroke="#3b82f6" strokeWidth={1.5} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} name="Y-axis" />
                      <Line type="linear" dataKey="z" stroke="#10b981" strokeWidth={1.5} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} name="Z-axis" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6 bg-secondary/10 rounded-lg w-full aspect-[4/3] border border-dashed border-border">
                  <div className="rounded-full bg-secondary w-10 h-10 flex items-center justify-center text-muted-foreground mb-2">
                    <svg className="w-5 h-5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <span className="text-sm font-medium text-muted-foreground">Waiting for IMU feed...</span>
                  <span className="text-[10px] text-muted-foreground/60 mt-1 max-w-[200px]">Ensure ESP32 is powered & streaming</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Live Gyroscope */}
          <Card className="border bg-card/60 backdrop-blur-md transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/30">
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <svg className="w-4 h-4 text-[#a855f7]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18" />
                </svg>
                Live Gyroscope (rad/s)
              </CardTitle>
              <div className="flex items-center gap-4">
                {gyroHistory.length > 0 && (
                  <div className="flex gap-2 text-[10px] font-mono border-r border-border/60 pr-4">
                    <span className="text-[#a855f7]">X: {gyroHistory[gyroHistory.length - 1].x.toFixed(2)}</span>
                    <span className="text-[#f97316]">Y: {gyroHistory[gyroHistory.length - 1].y.toFixed(2)}</span>
                    <span className="text-[#06b6d4]">Z: {gyroHistory[gyroHistory.length - 1].z.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex items-center gap-1 bg-secondary/30 p-0.5 rounded-lg border border-border/40">
                  {([50, 150, 300] as const).map((pts) => (
                    <button
                      key={pts}
                      onClick={() => setVisiblePoints(pts)}
                      className={`px-1.5 py-0.5 rounded text-[9px] font-medium transition-all ${
                        visiblePoints === pts
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary/40'
                      }`}
                    >
                      {pts}p
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="min-h-[260px] p-4 flex flex-col justify-between">
              {gyroHistory.length > 0 ? (
                <div className="w-full h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={gyroHistory.slice(-visiblePoints)} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                      <XAxis dataKey="ts" stroke="hsl(var(--muted-foreground))" fontSize={9} tickLine={false} axisLine={false} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={9} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                      <Tooltip
                        contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 11 }}
                        labelStyle={{ color: 'hsl(var(--foreground))' }}
                      />
                      <Line type="linear" dataKey="x" stroke="#a855f7" strokeWidth={1.5} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} name="X-axis" />
                      <Line type="linear" dataKey="y" stroke="#f97316" strokeWidth={1.5} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} name="Y-axis" />
                      <Line type="linear" dataKey="z" stroke="#06b6d4" strokeWidth={1.5} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} name="Z-axis" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6 bg-secondary/10 rounded-lg w-full aspect-[4/3] border border-dashed border-border">
                  <div className="rounded-full bg-secondary w-10 h-10 flex items-center justify-center text-muted-foreground mb-2">
                    <svg className="w-5 h-5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18" />
                    </svg>
                  </div>
                  <span className="text-sm font-medium text-muted-foreground">Waiting for IMU feed...</span>
                  <span className="text-[10px] text-muted-foreground/60 mt-1 max-w-[200px]">Ensure ESP32 is powered & streaming</span>
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
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="idx" hide />
                      <YAxis stroke="#9ca3af" fontSize={10} tickFormatter={(v) => `${v}ms`} />
                      <Tooltip
                        contentStyle={{ background: '#0f172a', border: '1px solid #1f2937', borderRadius: 8, fontSize: 12 }}
                        labelStyle={{ color: '#e2e8f0' }}
                        formatter={(value) => [`${Number(value).toFixed(1)}ms`]}
                      />
                      <Line type="monotone" dataKey="dtw" stroke="#38bdf8" strokeWidth={2} dot={false} name="DTW" />
                      <Line type="monotone" dataKey="fusion" stroke="#f59e0b" strokeWidth={2} dot={false} name="Fusion" />
                      <Legend iconSize={8} wrapperStyle={{ fontSize: 10, paddingTop: 4, color: '#e2e8f0' }} />
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
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="idx" hide />
                      <YAxis stroke="#9ca3af" fontSize={10} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                      <Tooltip
                        contentStyle={{ background: '#0f172a', border: '1px solid #1f2937', borderRadius: 8, fontSize: 12 }}
                        labelStyle={{ color: '#e2e8f0' }}
                        formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`]}
                      />
                      <defs>
                        <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.08} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="confidence" stroke="#38bdf8" strokeWidth={2} fill="url(#confGrad)" name="Confidence" />
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
