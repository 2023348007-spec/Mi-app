import 'package:flutter/material.dart';
import 'auth_service.dart';
import 'login_page.dart';
import 'foto_page.dart';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: FutureBuilder(
        future: AuthService().isLoggedIn(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.data == true) {
            return const FotoPage();
          } else {
            return const LoginPage();
          }
        },
      ),
      debugShowCheckedModeBanner: false,
    );
  }
}