/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ["@copilotkit/runtime", "type-graphql"],
  },
};

module.exports = nextConfig;
