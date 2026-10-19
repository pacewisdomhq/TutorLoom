// SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
// SPDX-License-Identifier: Apache-2.0

import 'package:tuturloom/utils/app_exports.dart';

/// An organization's resolved brand pair.
///
/// Built from `GET /api/organizations/{id}/` → `primary_color` / `accent_color`,
/// both of which are routinely `null` or `""`. A missing or unparseable colour
/// falls back to [AppBrand.fallback] — it must never throw and must never
/// produce a black theme.
@immutable
class AppBrand {
  const AppBrand({
    required this.primary,
    required this.accent,
    required this.usesDefaultRings,
  });

  final Color primary;
  final Color accent;

  /// True for the app's own default brand, whose rings use the built-in
  /// gradients rather than colours derived from an org's pair.
  final bool usesDefaultRings;

  /// The neutral in-app default, shown before an org is known.
  static const AppBrand fallback = AppBrand(
    primary: AppPalette.seedPrimary,
    accent: AppPalette.seedAccent,
    usesDefaultRings: true,
  );

  factory AppBrand.fromOrg(String? primaryHex, String? accentHex) {
    final Color? primary = parseHex(primaryHex);
    if (primary == null) return fallback;
    return AppBrand(
      primary: primary,
      accent: parseHex(accentHex) ?? primary,
      usesDefaultRings: false,
    );
  }

  static Color? parseHex(String? hex) {
    if (hex == null) return null;
    final String h = hex.trim().replaceFirst('#', '');
    if (!RegExp(r'^[0-9a-fA-F]{6}$').hasMatch(h)) return null;
    return Color(int.parse('FF$h', radix: 16));
  }

  /// Hex form, for persisting the resolved brand across launches.
  String get primaryHex => _hex(primary);
  String get accentHex => _hex(accent);

  static String _hex(Color c) {
    int channel(double v) => (v * 255).round().clamp(0, 255);
    return '#'
        '${channel(c.r).toRadixString(16).padLeft(2, '0')}'
        '${channel(c.g).toRadixString(16).padLeft(2, '0')}'
        '${channel(c.b).toRadixString(16).padLeft(2, '0')}';
  }

  /// Button and hero fills.
  Color fillFor(Brightness b) => deepenForWhiteText(
    b == Brightness.light
        ? primary
        : ensureContrast(primary, AppPalette.dSurface, 3.2),
  );

  /// Always white. See [deepenForWhiteText]: the fill is corrected so that it
  /// can be, rather than the label flipping to black on a brand green.
  Color onFillFor(Brightness b) => AppPalette.white;

  /// Brand-coloured text and icons (links, active tab, chips).
  Color textFor(Brightness b) => b == Brightness.light
      ? ensureContrast(primary, AppPalette.lSurface, 4.5)
      : ensureContrast(primary, AppPalette.dSurface, 4.5);

  /// The progress gradient: completion rings, progress bars, the home gauge.
  ///
  /// The default brand shades its **own primary** rather than reaching for a
  /// fixed pair. It used to be a hardcoded green-to-cyan, which meant the one
  /// brand the product ships with was the only one whose progress bars ignored
  /// its primary colour — every org that set a hex got a gradient built from
  /// it, and the product's own did not.
  List<Color> ring1() => usesDefaultRings
      ? <Color>[primary, Color.lerp(primary, AppPalette.white, 0.35)!]
      : <Color>[primary, Color.lerp(primary, accent, 0.45)!];

  @override
  bool operator ==(Object other) =>
      other is AppBrand &&
      other.primary == primary &&
      other.accent == accent &&
      other.usesDefaultRings == usesDefaultRings;

  @override
  int get hashCode => Object.hash(primary, accent, usesDefaultRings);
}
