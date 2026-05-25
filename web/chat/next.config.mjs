/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@excalidraw/excalidraw"],
  webpack: (config, { isServer }) => {
    config.resolve.alias = { ...config.resolve.alias, canvas: false };
    if (isServer) {
      const existing = Array.isArray(config.externals) ? config.externals : [];
      config.externals = [...existing, "@excalidraw/excalidraw"];
    }
    return config;
  },
};

export default nextConfig;
