declare module "neovis.js" {
  export default class NeoVis {
    static NEOVIS_ADVANCED_CONFIG: symbol;
    constructor(config: any);
    render(): void;
    clearNetwork(): void;
    renderWithCypher(cypher: string): void;
    registerOnEvent(event: string, callback: (event: any) => void): void;
    network: any;
    nodes: any;
  }
}
