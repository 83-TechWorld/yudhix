import { Capacitor } from '@capacitor/core';

/** Native-only polish when running inside the iOS / Android shell. No-op on the web. */
export async function initNative(): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  const [{ StatusBar, Style }, { SplashScreen }, { App }] = await Promise.all([
    import('@capacitor/status-bar'),
    import('@capacitor/splash-screen'),
    import('@capacitor/app'),
  ]);
  const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  await StatusBar.setStyle({ style: dark ? Style.Dark : Style.Light }).catch(() => {});
  await SplashScreen.hide().catch(() => {});
  // Android hardware back button: go back in the app instead of closing it.
  App.addListener('backButton', ({ canGoBack }) => (canGoBack ? history.back() : App.exitApp()));
}
