import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../pages/asset_detail_page.dart';
import '../pages/assets_page.dart';
import '../pages/connection_form_page.dart';
import '../pages/connections_page.dart';
import '../pages/dashboard_page.dart';
import '../pages/error_explorer_page.dart';
import '../pages/job_detail_page.dart';
import '../pages/jobs_page.dart';
import '../pages/pipeline_detail_page.dart';
import '../pages/pipeline_form_page.dart';
import '../pages/pipelines_page.dart';
import '../pages/settings_page.dart';
import '../widgets/layout/responsive_scaffold.dart';

final appRouter = GoRouter(
  initialLocation: '/dashboard',
  routes: [
    ShellRoute(
      builder: (context, state, child) => ResponsiveScaffold(child: child),
      routes: [
        GoRoute(path: '/dashboard', builder: (_, __) => const DashboardPage()),
        GoRoute(path: '/connections', builder: (_, __) => const ConnectionsPage()),
        GoRoute(
            path: '/connections/new',
            builder: (_, __) => const ConnectionFormPage()),
        GoRoute(
          path: '/connections/:id',
          builder: (_, state) =>
              ConnectionFormPage(id: state.pathParameters['id']),
        ),
        GoRoute(path: '/pipelines', builder: (_, __) => const PipelinesPage()),
        GoRoute(
            path: '/pipelines/new', builder: (_, __) => const PipelineFormPage()),
        GoRoute(
          path: '/pipelines/:id',
          builder: (_, state) =>
              PipelineDetailPage(id: state.pathParameters['id']!),
        ),
        GoRoute(
          path: '/pipelines/:id/edit',
          builder: (_, state) =>
              PipelineFormPage(id: state.pathParameters['id']),
        ),
        GoRoute(path: '/jobs', builder: (_, __) => const JobsPage()),
        GoRoute(
          path: '/jobs/:id',
          builder: (_, state) => JobDetailPage(id: state.pathParameters['id']!),
        ),
        GoRoute(path: '/errors', builder: (_, __) => const ErrorExplorerPage()),
        GoRoute(path: '/assets', builder: (_, __) => const AssetsPage()),
        GoRoute(
          path: '/assets/:key',
          builder: (_, state) => AssetDetailPage(
            assetKey: state.pathParameters['key']!,
          ),
        ),
        GoRoute(path: '/settings', builder: (_, __) => const SettingsPage()),
      ],
    ),
  ],
  errorBuilder: (context, state) => Scaffold(
    body: Center(child: Text('Not found: ${state.uri}')),
  ),
);
