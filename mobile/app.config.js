// Complète app.json au moment du build : l'API visée dépend du profil EAS (voir eas.json).
// Sans API_URL (expo start, profil preview), l'app parle à la production.
module.exports = ({ config }) => {
  const preprod = process.env.API_URL?.includes('preprod');
  return {
    ...config,
    // Une app « TopTroc preprod » s'installe à côté de la vraie, sans la remplacer.
    name: preprod ? `${config.name} preprod` : config.name,
    ios: { ...config.ios, bundleIdentifier: config.ios.bundleIdentifier + (preprod ? '.preprod' : '') },
    android: { ...config.android, package: config.android.package + (preprod ? '.preprod' : '') },
    extra: { ...config.extra, api: process.env.API_URL || config.extra.api },
  };
};
