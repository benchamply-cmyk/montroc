import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

// Une petite vibration aux moments qui comptent : un cœur, un match, une publication. Rien sur le web (aperçu).
export function vibrer(type: 'leger' | 'succes' = 'leger') {
  if (Platform.OS === 'web') return;
  const promesse =
    type === 'succes' ? Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success) : Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  promesse.catch(() => undefined);
}
