"use client";

import React, { useEffect, useRef, useState } from "react";
import { ListTree, RefreshCw, ZoomIn, ZoomOut, Layers, Info } from "lucide-react";
import cytoscape from "cytoscape";
import { apiFetch } from "../lib/api";

interface GraphExplorerProps {
  actorId?: string;
}

export const GraphExplorer: React.FC<GraphExplorerProps> = ({ actorId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadGraphData() {
      try {
        const actors = await apiFetch<any[]>("/api/v1/actors");
        const targetActorId = actorId || (actors[0] ? actors[0].id : "");
        if (!targetActorId) return;

        const graphData = await apiFetch<any>(`/api/v1/actors/${targetActorId}/graph`);

        const elements: cytoscape.ElementDefinition[] = [];

        (graphData.nodes || []).forEach((n: any) => {
          elements.push({
            data: { id: n.id, label: n.label, type: n.type },
          });
        });

        (graphData.edges || []).forEach((e: any) => {
          elements.push({
            data: { id: e.id, source: e.source, target: e.target, label: e.label },
          });
        });

        if (containerRef.current) {
          if (cyRef.current) {
            cyRef.current.destroy();
          }

          cyRef.current = cytoscape({
            container: containerRef.current,
            elements: elements,
            style: [
              {
                selector: "node",
                style: {
                  "background-color": "#5B18D6",
                  label: "data(label)",
                  color: "#F4F4F7",
                  "font-size": "11px",
                  "text-valign": "bottom",
                  "text-margin-y": 5,
                  width: 32,
                  height: 32,
                  "border-width": 2,
                  "border-color": "#8B2CFF",
                },
              },
              {
                selector: 'node[type = "Actor"]',
                style: {
                  "background-color": "#8B2CFF",
                  width: 42,
                  height: 42,
                  "border-color": "#19D9D0",
                  "border-width": 3,
                },
              },
              {
                selector: 'node[type = "PGPKey"]',
                style: {
                  "background-color": "#10B981",
                  width: 30,
                  height: 30,
                },
              },
              {
                selector: 'node[type = "Wallet"]',
                style: {
                  "background-color": "#19D9D0",
                  width: 30,
                  height: 30,
                },
              },
              {
                selector: "edge",
                style: {
                  width: 2,
                  "line-color": "#11131D",
                  "target-arrow-color": "#8B2CFF",
                  "target-arrow-shape": "triangle",
                  "curve-style": "bezier",
                  label: "data(label)",
                  "font-size": "9px",
                  color: "#A6A8B3",
                },
              },
              {
                selector: ":selected",
                style: {
                  "border-color": "#19D9D0",
                  "border-width": 4,
                  "line-color": "#19D9D0",
                },
              },
            ],
            layout: {
              name: "cose",
              animate: false,
            },
          });

          cyRef.current.on("tap", "node", (evt) => {
            const node = evt.target;
            setSelectedNode({
              id: node.id(),
              label: node.data("label"),
              type: node.data("type"),
            });
          });
        }
      } catch (err) {
        console.error("Failed loading graph", err);
      } finally {
        setLoading(false);
      }
    }

    loadGraphData();
  }, [actorId]);

  const handleRecenter = () => {
    if (cyRef.current) {
      cyRef.current.fit();
      cyRef.current.center();
    }
  };

  return (
    <div className="space-y-4">
      {/* Header Toolbar */}
      <div className="flex justify-between items-center border-b border-netra-border pb-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <ListTree className="w-5 h-5 text-netra-purple" />
            <span>Interactive Intelligence Knowledge Graph</span>
          </h1>
          <p className="text-xs text-netra-muted">
            Cytoscape.js Property Graph Visualizer • Rebuildable from PostgreSQL Evidence Ledger
          </p>
        </div>

        <div className="flex space-x-2">
          <button
            onClick={handleRecenter}
            className="p-2 rounded bg-netra-surface border border-netra-border text-netra-muted hover:text-white text-xs flex items-center space-x-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Fit Canvas</span>
          </button>
        </div>
      </div>

      {/* Main Canvas + Node Inspector Sidebar */}
      <div className="grid grid-cols-4 gap-4 h-[620px]">
        {/* Cytoscape Container (3 Cols) */}
        <div className="col-span-3 bg-netra-card border border-netra-border rounded-xl relative overflow-hidden glass-panel">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-netra-bg/80 z-20 text-xs font-mono text-netra-purple animate-pulse">
              Rendering Topology Graph...
            </div>
          )}
          <div ref={containerRef} className="w-full h-full" />
        </div>

        {/* Node Inspector Panel (1 Col) */}
        <div className="bg-netra-card border border-netra-border rounded-xl p-4 space-y-4 font-mono text-xs">
          <h2 className="font-semibold text-white border-b border-netra-border pb-2 flex items-center space-x-2">
            <Info className="w-4 h-4 text-netra-cyan" />
            <span>Node Inspector</span>
          </h2>

          {selectedNode ? (
            <div className="space-y-3">
              <div>
                <span className="text-netra-subtle">Node Type:</span>
                <div className="text-netra-purple font-bold">{selectedNode.type}</div>
              </div>

              <div>
                <span className="text-netra-subtle">Label / Handle:</span>
                <div className="text-white font-bold">{selectedNode.label}</div>
              </div>

              <div>
                <span className="text-netra-subtle">UUIDv7:</span>
                <div className="text-netra-muted text-[10px] break-all">{selectedNode.id}</div>
              </div>

              <div className="pt-2 border-t border-netra-border text-[11px] text-netra-valid">
                Linked to 4 Evidence Provenance Artifacts
              </div>
            </div>
          ) : (
            <div className="text-netra-subtle text-[11px] leading-relaxed">
              Click on any node in the canvas to inspect identity attributes, cryptographic keys, wallet clusters, and evidence links.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
