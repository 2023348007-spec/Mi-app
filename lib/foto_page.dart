import 'package:http_parser/http_parser.dart'; // Para MediaType
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:typed_data';
import 'dart:convert';
import 'auth_service.dart';
import 'login_page.dart';

class FotoPage extends StatefulWidget {
  const FotoPage({super.key});
  @override
  State<FotoPage> createState() => _FotoPageState();
}

class _FotoPageState extends State<FotoPage> {
  Uint8List? _imageBytes;
  XFile? _pickedFile;
  final picker = ImagePicker();
  final descripcionController = TextEditingController();
  String? uploadedImageUrl;
  bool _isUploading = false;

  Future getIImage() async {
    final pickedFile = await picker.pickImage(source: ImageSource.camera);
    if (pickedFile != null) {
      final bytes = await pickedFile.readAsBytes();
      setState(() {
        _imageBytes = bytes;
        _pickedFile = pickedFile;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Foto tomada correctamente ✅")),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("No se tomó ninguna foto ❌")),
      );
    }
  }

  Future subirFoto() async {
  if (_pickedFile == null || _imageBytes == null) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("¡Primero toma una foto!")),
    );
    return;
  }
  
  final authService = AuthService();
  final token = await authService.getToken();
  
  if (token == null) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("No estás autenticado")),
    );
    return;
  }

  setState(() {
    _isUploading = true;
  });

  try {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse("http://127.0.0.1:8001/fotos/"),
    );
    
    
    request.headers['Authorization'] = 'Bearer $token';
    request.headers['Content-Type'] = 'multipart/form-data';
    
    
    String descripcion = descripcionController.text.isEmpty 
        ? "Foto sin descripción" 
        : descripcionController.text;
    
    request.fields['descripcion'] = descripcion;

    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        _imageBytes!,
        filename: 'foto.jpg',
        contentType: MediaType('image', 'jpeg'),
      ),
    );

    print("Enviando foto..."); // Debug
    var response = await request.send();
    var respStr = await response.stream.bytesToString();

    print("Respuesta: ${response.statusCode} - $respStr"); // Debug

    if (response.statusCode == 200) {
      var data = json.decode(respStr);
      setState(() {
        uploadedImageUrl = data['foto']['ruta_foto'];
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Foto subida correctamente ✅"),
          backgroundColor: Colors.green,
        ),
      );
    } else {
      print("Error detallado: $respStr");
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Error ${response.statusCode}: $respStr"),
          backgroundColor: Colors.red,
        ),
      );
    }
  } catch (e) {
    print("Excepción: $e");
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("Error: $e"),
        backgroundColor: Colors.red,
      ),
    );
  } finally {
    setState(() {
      _isUploading = false;
    });
  }
}

  Widget mostrarImagenLocal() {
    if (_imageBytes == null) {
      return Container(
        width: 300,
        height: 200,
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.photo_camera, size: 50, color: Colors.grey),
            SizedBox(height: 10),
            Text("No hay imagen seleccionada"),
          ],
        ),
      );
    }
    return Image.memory(
      _imageBytes!,
      width: 300,
      height: 200,
      fit: BoxFit.cover,
    );
  }

  void _logout() async {
    await AuthService().logout();
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (context) => const LoginPage()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Subir Foto"),
        backgroundColor: Colors.blue,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _logout,
            tooltip: 'Cerrar Sesión',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            mostrarImagenLocal(),
            const SizedBox(height: 20),
            TextField(
              controller: descripcionController,
              decoration: const InputDecoration(
                labelText: "Descripción",
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.description),
              ),
            ),
            const SizedBox(height: 20),
            _isUploading
                ? const CircularProgressIndicator()
                : Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: getIImage,
                          icon: const Icon(Icons.camera_alt),
                          label: const Text("Tomar Foto"),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 15),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _isUploading ? null : subirFoto,
                          icon: const Icon(Icons.cloud_upload),
                          label: const Text("Subir a API"),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 15),
                            backgroundColor: Colors.green,
                          ),
                        ),
                      ),
                    ],
                  ),
            if (uploadedImageUrl != null) ...[
              const SizedBox(height: 20),
              const Text(
                "Última imagen subida:",
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Text(
                uploadedImageUrl!,
                style: const TextStyle(color: Colors.blue),
              ),
            ],
          ],
        ),
      ),
    );
  }
}