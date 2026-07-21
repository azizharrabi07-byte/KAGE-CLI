const stage = process.env.SST_STAGE || "dev"

export default {
  url: stage === "production" ? "https://kage.ai" : `https://${stage}.kage.ai`,
  console: stage === "production" ? "https://kage.ai/auth" : `https://${stage}.kage.ai/auth`,
  email: "help@anoma.ly",
  socialCard: "https://social-cards.sst.dev",
  github: "https://github.com/anomalyco/kage",
  discord: "https://kage.ai/discord",
  headerLinks: [
    { name: "app.header.home", url: "/" },
    { name: "app.header.docs", url: "/docs/" },
  ],
}
