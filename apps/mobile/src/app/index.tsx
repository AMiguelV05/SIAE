import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Image,
  KeyboardAvoidingView,
  Platform,
  Alert
} from 'react-native';
import { Feather } from '@expo/vector-icons'; // Librería para los íconos de usuario, candado y ojo
import { useRouter } from 'expo-router';

export default function LoginScreen() {
  const router = useRouter();
  const [codigo, setCodigo] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = () => {
    if (!codigo.trim() || !password.trim()) {
      Alert.alert('Campos incompletos', 'Por favor ingresa tu código y contraseña.');
      return;
    }

    //Navega a la ruta /home enviando el código del estudiante como parámetro
    router.replace({
      pathname: '/home',
      params: { codigo },
    });
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      {/*Franja verde superior*/}
      <View style={styles.topBar} />

      <View style={styles.content}>
        <Image
          source={require('../../assets/logo.png')} 
          style={styles.logo}
          resizeMode="contain"
        />

        {/*Textos de bienvenida*/}
        <Text style={styles.title}>BIENVENIDO</Text>
        <Text style={styles.subtitle}>SIAE</Text>
        <Text style={styles.instruction}>Ingresa tus datos para continuar</Text>

        {/*Input de código de estudiante*/}
        <View style={styles.inputContainer}>
          <Feather name="user" size={22} color="#888" style={styles.icon} />
          <TextInput
            style={styles.input}
            placeholder="Código de estudiante"
            placeholderTextColor="#A0A0A0"
            value={codigo}
            onChangeText={setCodigo}
            keyboardType="numeric"
            autoCapitalize="none"
          />
        </View>

        {/*Input de contraseña*/}
        <View style={styles.inputContainer}>
          <Feather name="lock" size={22} color="#888" style={styles.icon} />
          <TextInput
            style={styles.input}
            placeholder="Contraseña"
            placeholderTextColor="#A0A0A0"
            secureTextEntry={!showPassword}
            value={password}
            onChangeText={setPassword}
          />
          <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
            <Feather
              name={showPassword ? "eye" : "eye-off"}
              size={22}
              color="#000"
              style={styles.eyeIcon}
            />
          </TouchableOpacity>
        </View>

        {/*Link para "olvidaste tu contraseña?"*/}
        <TouchableOpacity style={styles.forgotPasswordContainer}>
          <Text style={styles.forgotPasswordText}>¿Olvidaste tu contraseña?</Text>
        </TouchableOpacity>

        {/*Botón iniciar sesión*/}
        <TouchableOpacity style={styles.button} onPress={handleLogin}>
          <Text style={styles.buttonText}>Iniciar sesión</Text>
        </TouchableOpacity>

        {/*Link de regístrate*/}
        <TouchableOpacity style={styles.registerContainer}>
          <Text style={styles.registerText}>¿No tienes cuenta? Regístrate</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F4F4F4', // Fondo gris muy claro
  },
  topBar: {
    height: '18%', 
    backgroundColor: '#CAFF70', // Verde lima superior
    width: '100%',
    position: 'absolute',
    top: 0,
    borderBottomLeftRadius: 10,
    borderBottomRightRadius: 10,
    zIndex: 1,      //para iOS
    elevation: 1,   //para android
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 25,
    paddingTop: 80, // Para evitar que el contenido pise la franja verde
  },
  logo: {
    width: 140,
    height: 140,
    marginBottom: 25,
  },
  title: {
    fontSize: 32,
    fontWeight: '900',
    color: '#000',
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 26,
    color: '#000',
    marginBottom: 15,
  },
  instruction: {
    fontSize: 15,
    color: '#999',
    marginBottom: 30,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EBEBEB',
    borderWidth: 3,
    borderColor: '#4CC3FF',// Azul claro de los bordes
    borderRadius: 35, //Bordes muy redondeados
    width: '100%',
    height: 60,
    marginBottom: 20,
    paddingHorizontal: 15,
  },
  icon: {
    marginRight: 10,
  },
  eyeIcon: {
    marginLeft: 10,
  },
  input: {
    flex: 1,
    height: '100%',
    color: '#333',
    fontSize: 16,
  },
  forgotPasswordContainer: {
    width: '100%',
    alignItems: 'flex-end',
    marginBottom: 35,
    paddingRight: 10,
  },
  forgotPasswordText: {
    color: '#0047AB',// Azul oscuro para el texto
    fontSize: 15,
    fontWeight: '500',
  },
  button: {
    backgroundColor: '#4CC3FF',// Azul claro
    borderRadius: 35,
    width: '90%',
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonText: {
    color: '#FFF',
    fontSize: 22,
    fontWeight: '500',
  },
  registerContainer: {
    marginTop: 25,
    alignItems: 'center',
    width: '100%',
  },
  registerText: {
    color: '#0047AB',
    fontSize: 15,
    fontWeight: '500',
  },
});