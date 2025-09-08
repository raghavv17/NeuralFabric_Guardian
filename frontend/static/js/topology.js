// Topology visualization using D3.js
class TopologyRenderer {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.width = 0;
        this.height = 0;
        this.svg = null;
        this.simulation = null;
        this.nodes = [];
        this.links = [];
        this.jobs = [];
        
        this.initializeRenderer();
    }

    initializeRenderer() {
        // Clear existing content
        this.container.selectAll("*").remove();
        
        // Get container dimensions
        const rect = this.container.node().getBoundingClientRect();
        this.width = rect.width || 800;
        this.height = rect.height || 400;
        
        // Create SVG
        this.svg = this.container.append("svg")
            .attr("width", this.width)
            .attr("height", this.height)
            .style("background", "rgba(0,0,0,0.1)");
        
        // Create groups for different elements
        this.linkGroup = this.svg.append("g").attr("class", "links");
        this.nodeGroup = this.svg.append("g").attr("class", "nodes");
        this.labelGroup = this.svg.append("g").attr("class", "labels");
        
        // Setup zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {
                this.svg.selectAll("g").attr("transform", event.transform);
            });
        
        this.svg.call(zoom);
        
        // Initialize force simulation
        this.simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100).strength(0.5))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(this.width / 2, this.height / 2))
            .force("collision", d3.forceCollide().radius(30));
    }

    updateTopology(topologyData) {
        this.nodes = topologyData.nodes || [];
        this.links = topologyData.edges || [];
        this.jobs = topologyData.jobs || [];
        
        this.renderNodes();
        this.renderLinks();
        this.renderLabels();
        this.startSimulation();
    }

    renderNodes() {
        const nodeSelection = this.nodeGroup.selectAll(".node")
            .data(this.nodes, d => d.id);

        nodeSelection.exit().remove();

        const nodeEnter = nodeSelection.enter().append("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", this.dragstarted.bind(this))
                .on("drag", this.dragged.bind(this))
                .on("end", this.dragended.bind(this)));

        // Add circles for nodes
        nodeEnter.append("circle")
            .attr("r", d => d.type === 'GPU' ? 20 : 15)
            .attr("fill", d => this.getNodeColor(d.type))
            .attr("stroke", "#ffffff")
            .attr("stroke-width", 2);

        // Add icons or text
        nodeEnter.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "0.35em")
            .attr("font-size", "10px")
            .attr("fill", "white")
            .text(d => d.type === 'GPU' ? '🎮' : '🔀');

        // Merge enter and update selections
        const nodeUpdate = nodeEnter.merge(nodeSelection);
        
        // Add hover effects
        nodeUpdate
            .on("mouseover", this.showNodeTooltip.bind(this))
            .on("mouseout", this.hideTooltip.bind(this));

        nodeUpdate.select("circle")
            .attr("fill", d => this.getNodeColor(d.type));
    }

    renderLinks() {
        const linkSelection = this.linkGroup.selectAll(".link")
            .data(this.links, d => d.id);

        linkSelection.exit().remove();

        const linkEnter = linkSelection.enter().append("line")
            .attr("class", "link")
            .attr("stroke-width", d => this.getLinkWidth(d.data))
            .attr("stroke", d => this.getLinkColor(d.data));

        const linkUpdate = linkEnter.merge(linkSelection);
        
        // Add hover effects for links
        linkUpdate
            .on("mouseover", this.showLinkTooltip.bind(this))
            .on("mouseout", this.hideTooltip.bind(this));

        // Update link appearance based on health
        linkUpdate
            .attr("stroke", d => this.getLinkColor(d.data))
            .attr("stroke-width", d => this.getLinkWidth(d.data))
            .attr("opacity", d => Math.max(0.3, d.data?.health_score || 1.0));
    }

    renderLabels() {
        const labelSelection = this.labelGroup.selectAll(".label")
            .data(this.nodes, d => d.id);

        labelSelection.exit().remove();

        const labelEnter = labelSelection.enter().append("text")
            .attr("class", "label")
            .attr("text-anchor", "middle")
            .attr("dy", "25px")
            .attr("font-size", "11px")
            .attr("fill", "#e0e0e0")
            .text(d => d.id);

        labelEnter.merge(labelSelection);
    }

    startSimulation() {
        this.simulation
            .nodes(this.nodes)
            .on("tick", this.ticked.bind(this));

        this.simulation.force("link")
            .links(this.links);

        this.simulation.alpha(1).restart();
    }

    ticked() {
        // Update link positions
        this.linkGroup.selectAll(".link")
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        // Update node positions
        this.nodeGroup.selectAll(".node")
            .attr("transform", d => `translate(${d.x},${d.y})`);

        // Update label positions
        this.labelGroup.selectAll(".label")
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    }

    getNodeColor(type) {
        const colors = {
            'GPU': '#64ffda',
            'Switch': '#ff6b6b',
            'default': '#54a0ff'
        };
        return colors[type] || colors.default;
    }

    getLinkColor(linkData) {
        const health = linkData?.health_score || 1.0;
        const interconnectType = linkData?.type || 'PCIe';
        
        // Base colors by interconnect type
        const baseColors = {
            'NVLink': '#27ae60',    // Green
            'UALink': '#3498db',    // Blue
            'PCIe': '#f39c12'       // Orange
        };
        
        // Modify based on health
        if (health < 0.3) return '#e74c3c';      // Critical - Red
        if (health < 0.6) return '#f39c12';      // Warning - Orange
        return baseColors[interconnectType] || '#27ae60';  // Healthy
    }

    getLinkWidth(linkData) {
        const utilization = linkData?.utilization || 0;
        const health = linkData?.health_score || 1.0;
        
        let width = 2 + (utilization * 4); // 2-6px based on utilization
        
        // Increase width for unhealthy links to make them more visible
        if (health < 0.5) width += 2;
        
        return Math.max(1, Math.min(8, width));
    }

    clearTopology() {
    // Remove all existing nodes, links, labels from the SVG
    if (this.linkGroup) this.linkGroup.selectAll("*").remove();
    if (this.nodeGroup) this.nodeGroup.selectAll("*").remove();
    if (this.labelGroup) this.labelGroup.selectAll("*").remove();

    // Reset internal data
    this.nodes = [];
    this.links = [];
    this.jobs = [];

    // Stop the force simulation if running
    if (this.simulation) {
        this.simulation.stop();
    }
}


    showNodeTooltip(event, d) {
        const tooltip = this.createTooltip();
        
        let content = `<strong>${d.id}</strong><br/>`;
        content += `Type: ${d.type}<br/>`;
        
        if (d.data) {
            if (d.data.compute_capability) {
                content += `Compute: ${d.data.compute_capability}<br/>`;
            }
            if (d.data.memory_gb) {
                content += `Memory: ${d.data.memory_gb}GB<br/>`;
            }
            if (d.data.ports) {
                content += `Ports: ${d.data.ports}<br/>`;
            }
        }
        
        tooltip.innerHTML = content;
        this.positionTooltip(tooltip, event);
    }

    showLinkTooltip(event, d) {
        const tooltip = this.createTooltip();
        
        let content = `<strong>${d.id}</strong><br/>`;
        content += `Type: ${d.data?.type || 'Unknown'}<br/>`;
        content += `Bandwidth: ${d.data?.bandwidth_gbps || 0}GB/s<br/>`;
        content += `Latency: ${d.data?.base_latency_us || 0}μs<br/>`;
        content += `Utilization: ${((d.data?.utilization || 0) * 100).toFixed(1)}%<br/>`;
        content += `Health: ${((d.data?.health_score || 1.0) * 100).toFixed(1)}%<br/>`;
        
        tooltip.innerHTML = content;
        this.positionTooltip(tooltip, event);
    }

    createTooltip() {
        let tooltip = document.getElementById('topology-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'topology-tooltip';
            tooltip.className = 'tooltip';
            tooltip.style.cssText = `
                position: absolute;
                background: rgba(0,0,0,0.9);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                pointer-events: none;
                z-index: 1000;
                border: 1px solid rgba(255,255,255,0.2);
                max-width: 200px;
            `;
            document.body.appendChild(tooltip);
        }
        
        tooltip.style.display = 'block';
        return tooltip;
    }

    positionTooltip(tooltip, event) {
        const rect = this.container.node().getBoundingClientRect();
        const x = event.pageX + 10;
        const y = event.pageY - 10;
        
        tooltip.style.left = x + 'px';
        tooltip.style.top = y + 'px';
    }

    hideTooltip() {
        const tooltip = document.getElementById('topology-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }

    dragstarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    updateLinkHealth(healthData) {
        // Update link health scores
        this.links.forEach(link => {
            if (healthData[link.id] !== undefined) {
                if (!link.data) link.data = {};
                link.data.health_score = healthData[link.id];
            }
        });
        
        // Re-render links with updated health
        this.renderLinks();
    }

    highlightPath(path) {
        // Reset all link styles
        this.linkGroup.selectAll(".link")
            .attr("stroke-width", d => this.getLinkWidth(d.data))
            .attr("stroke", d => this.getLinkColor(d.data))
            .attr("opacity", d => Math.max(0.3, d.data?.health_score || 1.0));

        // Highlight path
        if (path && path.length > 1) {
            for (let i = 0; i < path.length - 1; i++) {
                const source = path[i];
                const target = path[i + 1];
                
                this.linkGroup.selectAll(".link")
                    .filter(d => 
                        (d.source.id === source && d.target.id === target) ||
                        (d.source.id === target && d.target.id === source)
                    )
                    .attr("stroke", "#ff6b6b")
                    .attr("stroke-width", 6)
                    .attr("opacity", 1.0);
            }
        }
    }
}

// Global topology renderer instance
let topologyRenderer = null;

// Initialize topology visualization
function initializeTopology() {
    topologyRenderer = new TopologyRenderer('topologyViz');
}

// Load and display topology
function loadTopology() {
    const loadingEl = document.getElementById('topologyLoading');
    if (loadingEl) loadingEl.style.display = 'block';
    
    fetch('/api/topology')
        .then(response => response.json())
        .then(data => {
            if (topologyRenderer) {
                topologyRenderer.updateTopology(data);
            }
        })
        .catch(error => {
            console.error('Error loading topology:', error);
        })
        .finally(() => {
            if (loadingEl) loadingEl.style.display = 'none';
        });
}

// Update topology with health data
function updateTopologyHealth() {
    if (!topologyRenderer) return;
    
    fetch('/api/telemetry/health')
        .then(response => response.json())
        .then(healthData => {
            topologyRenderer.updateLinkHealth(healthData);
        })
        .catch(error => {
            console.error('Error updating topology health:', error);
        });
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTopology);
} else {
    initializeTopology();
}