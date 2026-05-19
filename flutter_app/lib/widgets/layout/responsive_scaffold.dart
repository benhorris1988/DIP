import 'package:flutter/material.dart';

import 'app_header.dart';
import 'app_sidebar.dart';

/// Sidebar permanently visible on wide layouts, drawer on narrow ones.
class ResponsiveScaffold extends StatelessWidget {
  const ResponsiveScaffold({super.key, required this.child});
  final Widget child;

  static const double breakpoint = 900;

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= breakpoint;
    if (wide) {
      return Scaffold(
        body: Row(
          children: [
            const AppSidebar(),
            Expanded(
              child: Column(
                children: [
                  const AppHeader(),
                  Expanded(child: child),
                ],
              ),
            ),
          ],
        ),
      );
    }
    return _NarrowScaffold(child: child);
  }
}

class _NarrowScaffold extends StatefulWidget {
  const _NarrowScaffold({required this.child});
  final Widget child;

  @override
  State<_NarrowScaffold> createState() => _NarrowScaffoldState();
}

class _NarrowScaffoldState extends State<_NarrowScaffold> {
  final _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      drawer: Drawer(
        child: AppSidebar(
          onItemTap: () => Navigator.of(context).pop(),
        ),
      ),
      appBar: AppHeader(
        showMenuButton: true,
        onMenu: () => _scaffoldKey.currentState?.openDrawer(),
      ),
      body: widget.child,
    );
  }
}
