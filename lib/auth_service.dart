import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthService {
  static const String baseUrl = "http://127.0.0.1:8001";
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'email': email,
          'password': password,
        }),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        await _storage.write(key: 'token', value: data['access_token']);
        return true;
      }
      return false;
    } catch (e) {
      print('Error en login: $e');
      return false;
    }
  }

  Future<String?> getToken() async {
    return await _storage.read(key: 'token');
  }

  Future<void> logout() async {
    await _storage.delete(key: 'token');
  }

  Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null;
  }
}