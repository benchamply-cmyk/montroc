import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { useEffect } from 'react';
import { Platform } from 'react-native';

import { api } from './api';
import type { Moi } from './types';

// Une notification reçue app ouverte s'affiche quand même en bannière.
Notifications.setNotificationHandler({
  handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }),
});

/** Demande l'accord (une fois), puis envoie le jeton Expo de ce téléphone à l'API. Rien sur le web ni en simulateur. */
async function enregistrer() {
  if (Platform.OS === 'web' || !Device.isDevice) return;
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', { name: 'TopTroc', importance: Notifications.AndroidImportance.HIGH });
  }
  let { status } = await Notifications.getPermissionsAsync();
  if (status === 'undetermined') status = (await Notifications.requestPermissionsAsync()).status;
  if (status !== 'granted') return;
  const projectId = Constants.expoConfig?.extra?.eas?.projectId as string | undefined;
  const { data: jeton } = await Notifications.getExpoPushTokenAsync({ projectId });
  await api('/moi/appareils', { corps: { jeton, plateforme: Platform.OS } });
}

/**
 * Notifications push (match, proposition, Grand Troc) : l'accord est demandé une fois connecté, quand elles servent ;
 * toucher une notification ouvre l'écran qu'elle désigne (« /echanges », « /echange/12 »).
 */
export function useNotifications(moi: Moi | null) {
  const membre = moi?.id;
  useEffect(() => {
    if (membre) enregistrer().catch(() => undefined);
  }, [membre]);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    const ouvrir = (r: Notifications.NotificationResponse | null) => {
      const chemin = r?.notification.request.content.data?.chemin;
      if (typeof chemin === 'string' && chemin.startsWith('/')) router.push(chemin as never);
    };
    // App fermée : la notification qui l'a ouverte.
    Notifications.getLastNotificationResponseAsync().then(ouvrir).catch(() => undefined);
    const abonnement = Notifications.addNotificationResponseReceivedListener(ouvrir);
    return () => abonnement.remove();
  }, []);
}
