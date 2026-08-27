import type { NextConfig } from "next";

const svgr = {
  loader: "@svgr/webpack",
  options: {
    svgoConfig: {
      plugins: [
        {
          name: "preset-default",
          params: {
            overrides: {
              removeViewBox: false,
            },
          },
        },
      ],
    },
  },
};

const nextConfig: NextConfig = {
  // Required by apps/frontend/Dockerfile (Next standalone server).
  output: "standalone",
  webpack(config) {
    config.module.rules.push({
      test: /\.svg$/,
      use: [svgr],
    });
    return config;
  },
  turbopack: {
    rules: {
      "*.svg": {
        loaders: [svgr],
        as: "*.js",
      },
    },
  },
};

export default nextConfig;
