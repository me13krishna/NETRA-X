"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { ListTree, Maximize2, ZoomIn, ZoomOut, Info } from "lucide-react";
import cytoscape from "cytoscape";
import { apiFetch } from "../lib/api";

interface GraphExplorerProps {
  actorId?: string;
}

interface InspectedNode {
  id: string;
  label: string;
  type: string;
  degree: number;
  links: { label: string; confidence: number; peer: string }[];
}

/*
  Palette note. This component previously carried the pre-redesign purple/cyan
  hexes (#5B18D6 / #8B2CFF / #19D9D0 / #10B981) hard-coded inside the Cytoscape
  style array. The Tailwind token remap could not reach them -- they are raw
  strings in a JS object, not class names -- so the canvas stayed on the
  abandoned palette while every panel around it moved to Tactical Telemetry.
  That mismatch, not the layout, was what made the graph read as broken.

  Node identity is now carried by SHAPE, not hue, for two reasons: the system
  permits exactly one accent colour, and shape survives colour-blindness and
  greyscale printing where a hue key does not.
*/
const C_GROUND = "#0A0A0A";
const C_PHOSPHOR = "#EAEAEA";

/*
  Everything previously sat at one contrast level -- thin grey outlines on a
  near-black ground -- so nothing separated at a glance. Node surfaces are now
  lifted well clear of the background, and role is carried by a small set of
  purposeful colours taken from the tokens the design system already defines
  for status readouts (amber = flagged, green = verified) rather than by
  decorative hues.
*/
const C = {
  ground: "#0A0A0A",
  hazard: "#E61919",       // the actor -- the subject
  amber: "#F0A020",        // a shared identifier -- the finding
  phosphor: "#EAEAEA",
  rule: "#282828",
  edge: "#55535080",
  edgeLive: "#EAEAEA",
  muted: "#9A9A9A",
  surface: "#2A2A2A",      // was #141414: nodes were nearly the ground colour
  surfaceLift: "#343434",
};

const NODE_SHAPES: Record<string, string> = {
  Actor: "hexagon",
  Alias: "ellipse",
  Account: "ellipse",
  PGPKey: "diamond",
  Wallet: "rectangle",
  OnionService: "hexagon",
  Server: "rectangle",
};

/*
  Node glyphs. Cytoscape paints to canvas, so an icon font or a React component
  is not an option -- the only thing it accepts is an image URL. These are
  inlined as data URIs so they need no network round trip and cannot 404.
  Stroke colour is baked in per icon: the Actor sits on a hazard-red fill and
  therefore needs a dark glyph, everything else sits on the dark surface.
*/
const ico = (svg: string) =>
  "data:image/svg+xml;utf8," + encodeURIComponent(svg.replace(/\s+/g, " ").trim());

const glyph = (body: string, stroke: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;

const ICON = {
  // Crosshair: the subject under investigation.
  actor: ico(glyph('<circle cx="12" cy="12" r="7"/><path d="M12 1.5v3.5M12 19v3.5M1.5 12h3.5M19 12h3.5"/><circle cx="12" cy="12" r="2.1"/>', C_GROUND)),
  linkedActor: ico(glyph('<circle cx="12" cy="12" r="7"/><path d="M12 1.5v3.5M12 19v3.5M1.5 12h3.5M19 12h3.5"/><circle cx="12" cy="12" r="2.1"/>', "#E61919")),
  sharedHandle: ico(glyph('<circle cx="9" cy="8.5" r="3"/><circle cx="16" cy="15" r="3"/><path d="M4 19.5c0-2.6 2.2-4.4 5-4.4M11 5.5c2.8 0 5 1.8 5 4.4"/>', "#F0A020")),
  sharedWallet: ico(glyph('<rect x="2.5" y="6.4" width="19" height="11.6" rx="1.6"/><path d="M2.5 10.4h19"/><path d="M12 13v3M9 14.5h6"/>', "#F0A020")),
  alias: ico(glyph('<circle cx="12" cy="8.2" r="3.5"/><path d="M5.2 19.8c0-3.5 3-5.9 6.8-5.9s6.8 2.4 6.8 5.9"/>', C_PHOSPHOR)),
  pgp: ico(glyph('<circle cx="8.2" cy="12" r="3.4"/><path d="M11.6 12h9.2M17.4 12v3.4M20.4 12v2.4"/>', C_PHOSPHOR)),
  wallet: ico(glyph('<rect x="3" y="6.4" width="18" height="11.6" rx="1.6"/><path d="M3 10.4h18"/><circle cx="17" cy="14.4" r="1"/>', C_PHOSPHOR)),
  onion: ico(glyph('<circle cx="12" cy="12" r="8.4"/><ellipse cx="12" cy="12" rx="3.9" ry="8.4"/><path d="M3.6 12h16.8"/>', C_PHOSPHOR)),
  server: ico(glyph('<rect x="3" y="4.4" width="18" height="6" rx="1.4"/><rect x="3" y="13.6" width="18" height="6" rx="1.4"/><path d="M6.4 7.4h.01M6.4 16.6h.01"/>', C_PHOSPHOR)),
};

export const GraphExplorer: React.FC<GraphExplorerProps> = ({ actorId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  // Monotonic request counter. A plain "disposed" boolean cannot tell an
  // unmount apart from "a newer actor was selected while this fetch was in
  // flight" -- and in the latter case the stale run would return early without
  // ever clearing `loading`, leaving the overlay stuck over a blank canvas.
  const reqRef = useRef(0);
  const [selectedNode, setSelectedNode] = useState<InspectedNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const [actors, setActors] = useState<any[]>([]);
  // "" means the full map. The per-actor view is still reachable from the
  // dropdown, but the map is the default because the product's claim is about
  // links *between* personas, not about one persona's attachments.
  const [selectedId, setSelectedId] = useState<string>(actorId ?? "");
  const [query, setQuery] = useState("");

  const inspect = useCallback((node: cytoscape.NodeSingular): InspectedNode => {
    const links = node
      .connectedEdges()
      .map((e) => {
        const peer = e.source().id() === node.id() ? e.target() : e.source();
        return {
          label: String(e.data("label") || "LINKED"),
          confidence: Number(e.data("confidence") ?? 0),
          peer: String(peer.data("label") || peer.id()),
        };
      })
      .sort((a, b) => b.confidence - a.confidence);

    return {
      id: node.id(),
      label: node.data("label"),
      type: node.data("type"),
      degree: node.degree(false),
      links,
    };
  }, []);

  useEffect(() => {
    let disposed = false;
    const req = ++reqRef.current;
    const stale = () => disposed || req !== reqRef.current;

    async function loadGraphData() {
      try {
        const list = await apiFetch<any[]>("/api/v1/actors");
        if (stale()) return;
        setActors(list);
        // An empty selection means the full map. Falling back to list[0] here
        // would silently turn the default view back into a single ego graph.
        const graphData = selectedId
          ? await apiFetch<any>(`/api/v1/actors/${selectedId}/graph`)
          : await apiFetch<any>("/api/v1/graph");
        if (stale() || !containerRef.current) return;

        const elements: cytoscape.ElementDefinition[] = [];

        (graphData.nodes || []).forEach((n: any) => {
          elements.push({
            data: {
              id: n.id,
              label: n.label,
              type: n.type,
              // Carried so search can match a wallet's chain list or an actor's
              // category, not just the visible label.
              sharedBy: n.shared_by ?? 0,
              detail: n.detail ?? "",
              category: n.category ?? "",
            },
          });
        });

        (graphData.edges || []).forEach((e: any) => {
          elements.push({
            data: {
              id: e.id,
              source: e.source,
              target: e.target,
              label: e.label,
              confidence: typeof e.confidence === "number" ? e.confidence : 0.9,
            },
          });
        });

        setStats({
          nodes: (graphData.nodes || []).length,
          edges: (graphData.edges || []).length,
        });

        if (cyRef.current) cyRef.current.destroy();

        const cy = cytoscape({
          container: containerRef.current,
          elements,
          minZoom: 0.25,
          maxZoom: 3,
          style: [
            {
              selector: "node",
              style: {
                shape: "ellipse",
                "background-color": C.surface,
                "border-width": 2,
                "border-color": C.muted,
                width: 48,
                height: 48,
                "background-image": ICON.alias,
                "background-fit": "none",
                "background-width": "50%",
                "background-height": "50%",
                "background-image-opacity": 0.92,
                label: "data(label)",
                color: C.phosphor,
                "font-family": "JetBrains Mono, IBM Plex Mono, monospace",
                "font-size": "11px",
                "text-valign": "bottom",
                "text-margin-y": 9,
                "text-max-width": "110px",
                "text-wrap": "ellipsis",
                // A hard plate behind the label so it stays legible when it
                // crosses an edge -- the alternative is hiding labels entirely.
                "text-background-color": C.ground,
                "text-background-opacity": 0.85,
                "text-background-padding": "3px",
                "transition-property": "opacity, border-color, background-color",
                "transition-duration": 140,
              },
            },
            // The subject of the investigation. Sole use of the accent colour.
            {
              selector: 'node[type = "Actor"]',
              style: {
                shape: "hexagon",
                "background-color": C.hazard,
                "border-color": C.hazard,
                "border-width": 2,
                width: 66,
                height: 66,
                "background-image": ICON.actor,
                "background-width": "44%",
                "background-height": "44%",
                "background-image-opacity": 1,
                "font-size": "13px",
                color: C.phosphor,
                "text-margin-y": 12,
              },
            },
            // A linked actor: same hexagon and glyph, outlined instead of filled,
            // so the actor under investigation remains visually unambiguous.
            {
              selector: 'node[type = "LinkedActor"]',
              style: {
                shape: "hexagon",
                "background-color": C.surface,
                "border-color": C.hazard,
                "border-width": 2,
                width: 62,
                height: 62,
                "background-image": ICON.linkedActor,
                "background-width": "44%",
                "background-height": "44%",
                "background-image-opacity": 1,
                "font-size": "12px",
                color: C.phosphor,
                "text-margin-y": 10,
              },
            },
            // A handle or wallet cluster touched by more than one persona. This
            // is the finding the whole system exists to surface, so it gets the
            // accent outline and grows with the number of actors involved.
            {
              selector: 'node[type = "SharedHandle"]',
              style: {
                shape: "round-rectangle",
                "background-color": C.surfaceLift,
                "border-color": C.amber,
                "border-width": 3,
                width: 92,
                height: 62,
                "background-image": ICON.sharedHandle,
                "background-width": "40%",
                "background-height": "40%",
                "font-size": "12px",
                color: C.amber,
                "text-margin-y": 10,
              },
            },
            {
              selector: 'node[type = "SharedWallet"]',
              style: {
                shape: "round-rectangle",
                "background-color": C.surfaceLift,
                "border-color": C.amber,
                "border-width": 3,
                width: 98,
                height: 64,
                "background-image": ICON.sharedWallet,
                "background-width": "40%",
                "background-height": "40%",
                "font-size": "11px",
                color: C.amber,
                "text-margin-y": 10,
              },
            },
            // Search hit.
            {
              selector: "node.match",
              style: {
                "border-color": "#4AF626",
                "border-width": 4,
                "text-background-color": "#0A0A0A",
                "text-background-opacity": 1,
                color: "#4AF626",
                "z-index": 40,
              },
            },
            {
              selector: 'node[type = "PGPKey"]',
              style: { shape: "diamond", width: 58, height: 58, "background-image": ICON.pgp, "background-width": "40%", "background-height": "40%", "border-color": C.phosphor },
            },
            {
              selector: 'node[type = "Wallet"]',
              style: { shape: "rectangle", width: 60, height: 44, "background-image": ICON.wallet, "background-width": "46%", "background-height": "46%", "border-color": C.phosphor },
            },
            {
              selector: 'node[type = "OnionService"]',
              style: { shape: "hexagon", width: 54, height: 54, "background-image": ICON.onion, "background-width": "46%", "background-height": "46%", "border-color": C.phosphor },
            },
            {
              selector: 'node[type = "Server"]',
              style: { shape: "rectangle", width: 56, height: 42, "background-image": ICON.server, "background-width": "46%", "background-height": "46%" },
            },
            {
              selector: "edge",
              style: {
                // Was #11131D -- effectively invisible against the ground, which
                // is why the graph read as unconnected dots.
                "line-color": "#565452",
                "target-arrow-color": "#565452",
                "target-arrow-shape": "triangle",
                "arrow-scale": 0.75,
                "curve-style": "bezier",
                // Edge weight carries confidence, per the roadmap: thickness is
                // proportional to how much the link is actually supported.
                width: "mapData(confidence, 0.4, 1, 1.5, 7)",
                label: "",
                "font-family": "JetBrains Mono, IBM Plex Mono, monospace",
                "font-size": "9px",
                color: C.muted,
                "text-background-color": C.ground,
                "text-background-opacity": 0.9,
                "text-background-padding": "2px",
                "transition-property": "line-color, target-arrow-color, opacity",
                "transition-duration": 140,
              },
            },
            // Focus states. Dimming the complement is what makes a dense graph
            // readable -- highlighting alone just adds more to look at.
            { selector: ".dim", style: { opacity: 0.18 } },
            { selector: "node.quiet", style: { "text-opacity": 0 } },
            {
              selector: "node.hl",
              style: { "border-color": C.hazard, "border-width": 2.5 },
            },
            {
              selector: "edge.hl",
              style: {
                "line-color": C.edgeLive,
                "target-arrow-color": C.edgeLive,
                "width": 4,
                label: "data(label)",
                // Deliberately NOT autorotate. Concentric radiates edges in every
                // direction, so rotation left vertical labels reading sideways.
                // Labels only appear on the focused edges, so the collisions
                // autorotate was solving cannot occur anyway.
                "z-index": 20,
              },
            },
            {
              selector: "node:selected",
              style: { "border-color": C.hazard, "border-width": 3 },
            },
          ] as any,
          layout: (selectedId
            ? {
                // Ego view: one actor ringed by its identifiers.
                name: "concentric",
                concentric: (n: any) => n.degree(),
                levelWidth: () => 1,
                minNodeSpacing: 78,
                padding: 64,
                avoidOverlap: true,
                animate: false,
              }
            : {
                // Full map: force-directed, because the shape of the web -- who
                // clusters around which shared identifier -- is the finding.
                name: "cose",
                animate: false,
                padding: 60,
                nodeRepulsion: () => 22000,
                idealEdgeLength: () => 110,
                edgeElasticity: () => 80,
                gravity: 28,
                componentSpacing: 150,
                nodeDimensionsIncludeLabels: true,
                randomize: false,
                numIter: 1600,
              }) as any,
        });

        cyRef.current = cy;
        cy.fit(undefined, 48);

        // A canvas has no DOM to query, so end-to-end tooling has no way to
        // address a node. Expose the instance so Playwright (and the console)
        // can resolve positions instead of guessing at pixel coordinates.
        if (typeof window !== "undefined") {
          (window as unknown as Record<string, unknown>).__NETRA_CY__ = cy;
        }

        const focus = (node: cytoscape.NodeSingular) => {
          const keep = node.closedNeighborhood();
          cy.elements().addClass("dim");
          keep.removeClass("dim").addClass("hl");
        };
        const clearFocus = () => cy.elements().removeClass("dim hl");

        cy.on("mouseover", "node", (evt) => focus(evt.target));
        cy.on("mouseout", "node", () => {
          const sel = cy.$("node:selected");
          if (sel.length) focus(sel[0] as cytoscape.NodeSingular);
          else clearFocus();
        });

        // Only name the actors and the shared identifiers until the analyst
        // zooms in; 86 simultaneous labels is noise, not information.
        const applyLabelDensity = () => {
          if (selectedId) return;                 // ego view is sparse enough
          const zoomed = cy.zoom() > 0.6;
          cy.nodes().forEach((n) => {
            const t = n.data("type");
            const always = t === "Actor" || t === "SharedHandle" || t === "SharedWallet";
            n.toggleClass("quiet", !always && !zoomed);
          });
        };
        applyLabelDensity();
        cy.on("zoom", applyLabelDensity);

        cy.on("tap", "node", (evt) => {
          setSelectedNode(inspect(evt.target));
          focus(evt.target);
        });

        cy.on("tap", (evt) => {
          if (evt.target === cy) {
            setSelectedNode(null);
            clearFocus();
          }
        });

        // Pointer affordance -- a canvas that does not change the cursor reads
        // as a static image.
        const el = containerRef.current;
        cy.on("mouseover", "node", () => { if (el) el.style.cursor = "pointer"; });
        cy.on("mouseout", "node", () => { if (el) el.style.cursor = "default"; });
      } catch (err) {
        console.error("Failed loading graph", err);
      } finally {
        // Clear the overlay whenever this is still the newest request, even if
        // the build failed -- a stuck spinner hides the error.
        if (!stale()) setLoading(false);
      }
    }

    loadGraphData();
    return () => {
      disposed = true;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [actorId, selectedId, inspect]);

  // Search runs against the live graph rather than refetching: the map is the
  // corpus, so finding a handle means locating it in place, not loading a new
  // view. Empty query restores the full map.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const q = query.trim().toLowerCase();
    cy.elements().removeClass("match dim hl");
    if (!q) return;

    const hits = cy.nodes().filter((n) => {
      const l = String(n.data("label") ?? "").toLowerCase();
      const d = String(n.data("detail") ?? "").toLowerCase();
      const c = String(n.data("category") ?? "").toLowerCase();
      return l.includes(q) || d.includes(q) || c.includes(q);
    });
    if (hits.length === 0) return;

    const keep = hits.closedNeighborhood();
    cy.elements().addClass("dim");
    keep.removeClass("dim");
    hits.removeClass("dim").addClass("match");
    cy.animate({ fit: { eles: keep, padding: 90 }, duration: 320 });
  }, [query, stats]);

  const zoomBy = (factor: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };

  const handleRecenter = () => {
    if (cyRef.current) cyRef.current.fit(undefined, 48);
  };

  const ctrl =
    "p-2 border border-netra-border bg-netra-surface text-netra-muted hover:text-white hover:border-netra-purple transition-colors";

  return (
    <div className="space-y-4">
      {/* Header Toolbar */}
      <div className="flex justify-between items-end border-b border-netra-border pb-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <ListTree className="w-5 h-5 text-netra-purple" />
            <span>Interactive Intelligence Knowledge Graph</span>
          </h1>
          <p className="text-xs text-netra-muted">
            Cytoscape.js Property Graph Visualizer • Rebuildable from PostgreSQL Evidence Ledger
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search handle, wallet, actor..."
            aria-label="Search the graph"
            className="bg-netra-surface border border-netra-border text-netra-text font-mono text-[11px] px-2 py-1.5 w-[210px] placeholder:text-netra-subtle focus:border-netra-purple outline-none"
          />
          {actors.length > 1 && (
            <select
              value={selectedId}
              onChange={(e) => {
                setSelectedId(e.target.value);
                setSelectedNode(null);
                setLoading(true);
              }}
              aria-label="Actor under investigation"
              className="bg-netra-surface border border-netra-border text-netra-text font-mono text-[11px] px-2 py-1.5 focus:border-netra-purple outline-none max-w-[230px]"
            >
              <option value="">— Full network map —</option>
              {actors.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.primary_alias} — {a.category}
                </option>
              ))}
            </select>
          )}
          <div className="font-mono text-[10px] uppercase tracking-telemetry text-netra-subtle text-right leading-relaxed">
            <div>
              <span className="text-netra-muted">{stats.nodes}</span> nodes
            </div>
            <div>
              <span className="text-netra-muted">{stats.edges}</span> edges
            </div>
          </div>
          <div className="flex">
            <button onClick={() => zoomBy(1.3)} className={ctrl} title="Zoom in" aria-label="Zoom in">
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button onClick={() => zoomBy(1 / 1.3)} className={`${ctrl} border-l-0`} title="Zoom out" aria-label="Zoom out">
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button onClick={handleRecenter} className={`${ctrl} border-l-0`} title="Fit canvas" aria-label="Fit canvas">
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas + Node Inspector Sidebar */}
      <div className="grid grid-cols-5 gap-4 h-[calc(100vh-208px)] min-h-[640px]">
        <div className="col-span-4 bg-netra-card border border-netra-border relative overflow-hidden glass-panel">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-netra-bg/80 z-20 text-xs font-mono text-netra-purple animate-pulse">
              Rendering Topology Graph...
            </div>
          )}
          <div
            ref={containerRef}
            className="w-full h-full"
            style={{
              backgroundImage:
                "linear-gradient(#1C1C1C 1px, transparent 1px), linear-gradient(90deg, #1C1C1C 1px, transparent 1px)",
              backgroundSize: "44px 44px",
            }}
          />

          {/* Shape key. Identity is encoded by geometry, so the legend has to
              show geometry -- a colour swatch key would be a lie here. */}
          {!loading && (
            <div className="absolute bottom-0 left-0 border-t border-r border-netra-border bg-netra-bg/95 px-3 py-2 font-mono text-[9px] uppercase tracking-telemetry text-netra-subtle flex items-center gap-x-4">
              <span className="flex items-center gap-x-1.5">
                <svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true">
                  <polygon points="5.5,0 11,3 11,8 5.5,11 0,8 0,3" fill="#E61919" />
                </svg>
                Actor
              </span>
              <span className="flex items-center gap-x-1.5">
                <svg width="14" height="11" viewBox="0 0 14 11" aria-hidden="true">
                  <rect x="0.8" y="1.4" width="12.4" height="8.2" rx="2" fill="#343434" stroke="#F0A020" strokeWidth="1.8" />
                </svg>
                Shared identifier
              </span>
              <span className="flex items-center gap-x-1.5">
                <svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true">
                  <circle cx="5.5" cy="5.5" r="4.4" fill="#141414" stroke="#8A8A8A" strokeWidth="1.4" />
                </svg>
                Handle
              </span>
              <span className="flex items-center gap-x-1.5">
                <svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true">
                  <polygon points="5.5,0.6 10.4,5.5 5.5,10.4 0.6,5.5" fill="#141414" stroke="#EAEAEA" strokeWidth="1.4" />
                </svg>
                PGP
              </span>
              <span className="flex items-center gap-x-1.5">
                <svg width="13" height="11" viewBox="0 0 13 11" aria-hidden="true">
                  <rect x="0.7" y="1.7" width="11.6" height="7.6" fill="#141414" stroke="#EAEAEA" strokeWidth="1.4" />
                </svg>
                Wallet
              </span>
              <span className="text-netra-subtle/70">| edge weight = confidence</span>
            </div>
          )}
        </div>

        {/* Node Inspector Panel */}
        <div className="bg-netra-card border border-netra-border p-4 space-y-4 font-mono text-xs overflow-y-auto">
          <h2 className="font-semibold text-white border-b border-netra-border pb-2 flex items-center space-x-2">
            <Info className="w-4 h-4 text-netra-cyan" />
            <span>Node Inspector</span>
          </h2>

          {selectedNode ? (
            <div className="space-y-3">
              <div>
                <span className="text-netra-subtle uppercase tracking-telemetry text-[10px]">Node Type</span>
                <div className="text-netra-purple font-bold">{selectedNode.type}</div>
              </div>

              <div>
                <span className="text-netra-subtle uppercase tracking-telemetry text-[10px]">Label / Handle</span>
                <div className="text-white font-bold break-all">{selectedNode.label}</div>
              </div>

              <div>
                <span className="text-netra-subtle uppercase tracking-telemetry text-[10px]">UUIDv7</span>
                <div className="text-netra-muted text-[10px] break-all">{selectedNode.id}</div>
              </div>

              <div className="pt-3 border-t border-netra-border">
                <span className="text-netra-subtle uppercase tracking-telemetry text-[10px]">
                  Linked Edges ({selectedNode.degree})
                </span>
                <div className="mt-2 space-y-2">
                  {selectedNode.links.map((l, i) => (
                    <div key={i} className="border-l border-netra-border pl-2">
                      <div className="text-netra-text text-[10px] break-all">{l.peer}</div>
                      <div className="flex items-center justify-between text-[9px] text-netra-subtle">
                        <span className="uppercase">{l.label}</span>
                        <span className="text-netra-valid">{(l.confidence * 100).toFixed(0)}%</span>
                      </div>
                      {/* Bar restates the confidence the edge thickness encodes,
                          so the value is never colour/width-only. */}
                      <div className="mt-1 h-[2px] bg-netra-border">
                        <div
                          className="h-full bg-netra-purple"
                          style={{ width: `${Math.max(2, l.confidence * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  {selectedNode.links.length === 0 && (
                    <div className="text-netra-subtle text-[10px]">No linked edges in this projection.</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-netra-subtle text-[11px] leading-relaxed">
              Hover a node to isolate its neighbourhood. Click to inspect identity attributes,
              cryptographic keys, wallet clusters, and the confidence behind each link.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
