// SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
// SPDX-License-Identifier: Apache-2.0

import 'dart:math' as math;

import 'package:tuturloom/utils/app_exports.dart';

/// The completion ring from the design: one arc over a flat track.
///
/// **One ring, one colour.** It drew up to three concentric rings on sweep
/// gradients, which is where the green came from — and both call sites, the
/// roadmap header and Progress, only ever passed a single value. So the
/// stagger machinery animated a stagger of one, and two of the three gradients
/// were never drawn. A percentage reads as the brand colour against the empty
/// track, which is the whole of what either screen is saying.
///
/// This also absorbs what was `ScoreRing`: the quiz result drew the same
/// circle with a pass/fail tint, through a second widget and a second painter.
/// It passes that tint as [color].
class LearningRing extends StatelessWidget {
  const LearningRing({
    super.key,
    required this.value,
    this.size = 136,
    this.stroke = 14,
    this.center,
    this.color,
  });

  /// 0..1. Anything outside that is clamped rather than wrapped around.
  final double value;

  final double size;
  final double stroke;

  /// Sits in the hole. Null draws the ring alone.
  final Widget? center;

  /// Overrides the brand fill — the quiz result tints it by pass or fail.
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final BrandColors brand = context.brand;

    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: value.clamp(0.0, 1.0)),
      duration: context.reduceMotion ? Duration.zero : AppMotion.ringDraw,
      curve: AppMotion.ring,
      builder: (BuildContext context, double drawn, Widget? child) => SizedBox(
        width: size,
        height: size,
        child: Stack(
          alignment: Alignment.center,
          children: <Widget>[
            CustomPaint(
              size: Size.square(size),
              painter: _RingPainter(
                value: drawn,
                color: color ?? brand.brandFill,
                track: brand.track,
                stroke: stroke,
              ),
            ),
            ?child,
          ],
        ),
      ),
      child: center,
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.value,
    required this.color,
    required this.track,
    required this.stroke,
  });

  final double value;
  final Color color;
  final Color track;
  final double stroke;

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = Offset(size.width / 2, size.height / 2);
    final double radius = (size.width / 2) - (stroke / 2);
    if (radius <= 0) return;

    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke
        ..color = track,
    );

    if (value <= 0) return;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      2 * math.pi * value,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke
        ..strokeCap = StrokeCap.round
        ..color = color,
    );
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.value != value || old.color != color || old.track != track;
}

/// `.bar`: an 8px track with a gradient fill that grows from the left.
class ProgressBar extends StatelessWidget {
  const ProgressBar({
    super.key,
    required this.value,
    this.height = 8,
    this.colors,
  });

  final double value;
  final double height;
  final List<Color>? colors;

  @override
  Widget build(BuildContext context) {
    final BrandColors brand = context.brand;
    final List<Color> fill = colors ?? brand.ring1;

    return ClipRRect(
      borderRadius: BorderRadius.circular(height / 2),
      child: SizedBox(
        height: height,
        child: Stack(
          children: <Widget>[
            Container(color: brand.track),
            TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0, end: value.clamp(0.0, 1.0)),
              duration: context.reduceMotion
                  ? Duration.zero
                  : AppMotion.countUp,
              curve: AppMotion.decelerate,
              // `heightFactor: 1` is load-bearing. Without it the inner
              // constraints stay loose vertically, and a childless
              // DecoratedBox takes the smallest size it is allowed — zero
              // height — so the gradient never appears and the bar reads as a
              // plain grey track at every percentage.
              builder: (_, double t, _) => FractionallySizedBox(
                alignment: Alignment.centerLeft,
                widthFactor: t,
                heightFactor: 1,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: fill),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// `.chip`: a stadium pill. [tone] picks the colour pair.
enum ChipTone { neutral, brand, success, warning, danger }

class AppChip extends StatelessWidget {
  const AppChip({
    super.key,
    required this.label,
    this.icon,
    this.tone = ChipTone.neutral,
  });

  final String label;
  final IconData? icon;
  final ChipTone tone;

  @override
  Widget build(BuildContext context) {
    final BrandColors b = context.brand;
    final (Color bg, Color fg) = switch (tone) {
      ChipTone.neutral => (context.colors.surfaceContainerHighest, b.muted),
      ChipTone.brand => (b.brandSoft, b.brandText),
      ChipTone.success => (b.successContainer, b.success),
      ChipTone.warning => (b.warningContainer, b.warning),
      ChipTone.danger => (b.dangerContainer, b.danger),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 13, color: fg),
            const SizedBox(width: 5),
          ],
          Flexible(
            child: Text(
              label,
              style: context.text.labelMedium?.copyWith(color: fg, height: 1),
            ),
          ),
        ],
      ),
    );
  }
}

/// `.card`: surface, hairline outline, 22px radius.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpace.lg),
    this.onTap,
  });

  final Widget child;
  final EdgeInsets padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final Widget box = Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: context.colors.surface,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: context.colors.outline),
      ),
      child: child,
    );
    return onTap == null ? box : PressScale(onTap: onTap, child: box);
  }
}
