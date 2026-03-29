import { pcIcon, laptopIcon, serverIcon, dcIcon, routerIcon, switchIcon } from "./icons-generated";

export function getDeviceIcon(
  deviceType: string, osType: string,
  _vendorCategory?: string | null, model?: string | null,
): string {
  if (deviceType === "router") return routerIcon;
  if (deviceType === "switch") return switchIcon;
  if (deviceType === "dc") return dcIcon;
  if (deviceType === "server") return serverIcon;
  const m = (model ?? "").toLowerCase();
  if (osType === "macos" || m.includes("book") || m.includes("laptop") ||
      m.includes("thinkpad") || m.includes("latitude") || m.includes("elitebook") ||
      m.includes("surface") || m.includes("yoga") || m.includes("air") ||
      m.includes("xps 13") || m.includes("xps 15"))
    return laptopIcon;
  return pcIcon;
}

export function getOsLabel(osType: string, vendorCategory?: string | null): string {
  const m: Record<string, string> = {
    cisco:"Cisco", fortinet:"Fortinet", ubiquiti:"Ubiquiti", hp:"HP",
    dell:"Dell", lenovo:"Lenovo", apple:"macOS",
  };
  if (vendorCategory && m[vendorCategory]) return m[vendorCategory];
  const o: Record<string, string> = { windows:"Windows", macos:"macOS", linux:"Linux", ios:"IOS" };
  return o[osType] ?? "";
}

export function getDeviceColor(deviceType: string, osType: string, vendorCategory?: string | null): string {
  if (vendorCategory === "cisco") return "#049fd9";
  if (vendorCategory === "fortinet") return "#DA291C";
  if (vendorCategory === "ubiquiti") return "#0559C9";
  if (vendorCategory === "dell") return "#007DB8";
  if (vendorCategory === "hp") return "#0096D6";
  if (vendorCategory === "lenovo") return "#E2231A";
  if (vendorCategory === "apple") return "#A2AAAD";
  if (deviceType === "router") return "#16a34a";
  if (deviceType === "switch") return "#0d9488";
  if (deviceType === "dc") return "#7c3aed";
  if (deviceType === "server") return "#475569";
  if (osType === "macos") return "#A2AAAD";
  if (osType === "linux") return "#EAB308";
  return "#0078D4";
}