// Compiler Expo SDK 54 avec Xcode 27 et le lancer sur iOS 27. À retirer quand le SDK Expo le fera lui-même.
// 1. iOS 27 refuse de lancer une app compilée avec son SDK si elle n'a pas adopté le cycle de vie UIScene,
//    ce que le modèle natif d'Expo SDK 54 ne fait pas. On ajoute le manifeste de scène et un SceneDelegate
//    qui rattache à la scène la fenêtre créée par l'AppDelegate : l'amorçage React Native et expo-dev-client ne changent pas.
// 2. Xcode 27 refuse une cible iOS inférieure à 15. Le post_install de React Native relève celle des pods,
//    mais pas celle de leurs bundles de ressources (SDWebImage-SDWebImage, d'expo-image, reste à iOS 9).
const fs = require('fs');
const path = require('path');
const { withDangerousMod, withInfoPlist, withPodfile, withXcodeProject, IOSConfig } = require('expo/config-plugins');

const POST_INSTALL = `  post_install do |installer|
    # with-ios-27 : aucune cible des pods (bundles de ressources compris) sous la cible iOS de l'app.
    cible_ios = podfile_properties['ios.deploymentTarget'] || '15.1'
    installer.pods_project.targets.each do |t|
      t.build_configurations.each do |c|
        v = c.build_settings['IPHONEOS_DEPLOYMENT_TARGET']
        c.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = cible_ios if v.nil? || Gem::Version.new(v) < Gem::Version.new(cible_ios)
      end
    end
`;

const SCENE_DELEGATE = `import UIKit

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
  private var appDelegate: AppDelegate? { UIApplication.shared.delegate as? AppDelegate }

  func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
    guard let windowScene = scene as? UIWindowScene, let window = appDelegate?.window else { return }
    window.windowScene = windowScene
    window.makeKeyAndVisible()
    // Lien ouvert au démarrage (lien de connexion, expo-dev-client) : iOS ne le passe plus à l'AppDelegate.
    self.scene(scene, openURLContexts: connectionOptions.urlContexts)
    if let activite = connectionOptions.userActivities.first {
      self.scene(scene, continue: activite)
    }
  }

  func scene(_ scene: UIScene, openURLContexts contexts: Set<UIOpenURLContext>) {
    for context in contexts {
      _ = appDelegate?.application(UIApplication.shared, open: context.url, options: [:])
    }
  }

  func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
    _ = appDelegate?.application(UIApplication.shared, continue: userActivity, restorationHandler: { _ in })
  }
}
`;

module.exports = function withIos27(config) {
  config = withPodfile(config, (c) => {
    if (!c.modResults.contents.includes('with-ios-27')) {
      c.modResults.contents = c.modResults.contents.replace(/^  post_install do \|installer\|\n/m, POST_INSTALL);
    }
    return c;
  });

  config = withInfoPlist(config, (c) => {
    c.modResults.UIApplicationSceneManifest = {
      UIApplicationSupportsMultipleScenes: false,
      UISceneConfigurations: {
        UIWindowSceneSessionRoleApplication: [
          {
            UISceneConfigurationName: 'Default Configuration',
            UISceneDelegateClassName: '$(PRODUCT_MODULE_NAME).SceneDelegate',
          },
        ],
      },
    };
    return c;
  });

  config = withDangerousMod(config, [
    'ios',
    (c) => {
      const dossier = path.join(c.modRequest.platformProjectRoot, c.modRequest.projectName);
      fs.writeFileSync(path.join(dossier, 'SceneDelegate.swift'), SCENE_DELEGATE);
      return c;
    },
  ]);

  return withXcodeProject(config, (c) => {
    const nom = c.modRequest.projectName;
    const fichier = `${nom}/SceneDelegate.swift`;
    if (!c.modResults.hasFile(fichier)) {
      IOSConfig.XcodeUtils.addBuildSourceFileToGroup({ filepath: fichier, groupName: nom, project: c.modResults });
    }
    return c;
  });
};
