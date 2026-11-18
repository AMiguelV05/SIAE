import React, { useState, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StatusBar,
  Platform,
  KeyboardAvoidingView,
  Alert,
} from 'react-native';
import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';

const MENSAJES_INICIALES = [
  {
    id: '1',
    remitente: 'usuario',
    texto: '¿Cuáles son los requisitos de titulación?',
  },
  {
    id: '2',
    remitente: 'bot',
    texto:
      'Hola! Los requisitos para la titulación en tu carrera son:\n\n' +
      '1. 398 créditos\n' +
      '2. 64 horas integrales\n' +
      '3. Acreditación del idioma inglés (B1)\n' +
      '4. Acreditación de prácticas profesionales\n' +
      '5. Acreditación del servicio social\n' +
      '6. Proyecto modular\n' +
      '7. Realización de Ceneval\n\n' +
      'Aquí tienes más información:',
    archivo: 'Requisitos_titulación.pdf',
  },
];

export default function ChatScreen() {
  const router = useRouter();
  const { codigo } = useLocalSearchParams();
  const scrollViewRef = useRef(null);

  const [mensajes, setMensajes] = useState(MENSAJES_INICIALES);
  const [inputText, setInputText] = useState('');

  const enviarMensaje = () => {
    if (!inputText.trim()) return;

    const nuevoMensajeUsuario = {
      id: Date.now().toString(),
      remitente: 'usuario',
      texto: inputText.trim(),
    };

    setMensajes((prev) => [...prev, nuevoMensajeUsuario]);
    setInputText('');

    //Respuesta simulada del asistente
    setTimeout(() => {
      const respuestaBot = {
        id: (Date.now() + 1).toString(),
        remitente: 'bot',
        texto:
          'Estoy consultando la información académica del SIAE para ayudarte con tu duda.',
      };
      setMensajes((prev) => [...prev, respuestaBot]);
    }, 600);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar backgroundColor="#CAFF70" barStyle="dark-content" />

      {/* Cabecera verde lima */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <TouchableOpacity
            onPress={() => router.back()}
            style={styles.backButton}
            accessibilityLabel="Regresar"
          >
            <Feather name="arrow-left" size={28} color="#000" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Asistente SIAE</Text>
        </View>

        <TouchableOpacity
          style={styles.avatarContainer}
          onPress={() =>
            Alert.alert('Perfil', `Código: ${codigo || 'Estudiante'}`)
          }
        >
          <Ionicons name="person" size={26} color="#FFD2A6" />
        </TouchableOpacity>
      </View>

      {/*Cuerpo del chat*/}
      <KeyboardAvoidingView
        style={styles.chatContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 20}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesList}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() =>
            scrollViewRef.current?.scrollToEnd({ animated: true })
          }
          showsVerticalScrollIndicator={false}
        >
          {mensajes.map((msg) => {
            if (msg.remitente === 'usuario') {
              return (
                <View key={msg.id} style={styles.userRow}>
                  <View style={styles.userBubble}>
                    <Text style={styles.userBubbleText}>{msg.texto}</Text>
                  </View>
                </View>
              );
            }

            return (
              <View key={msg.id} style={styles.botRow}>
                {/*Avatar circular del bot*/}
                <View style={styles.botAvatar}>
                  <MaterialCommunityIcons
                    name="robot-happy"
                    size={26}
                    color="#1E56C5"
                  />
                </View>

                <View style={styles.botMessagesColumn}>
                  <View style={styles.botBubble}>
                    <Text style={styles.botBubbleText}>{msg.texto}</Text>
                  </View>

                  {/*Etiqueta de documento adjunto*/}
                  {msg.archivo && (
                    <TouchableOpacity
                      style={styles.filePill}
                      onPress={() =>
                        Alert.alert('Documento', `Abriendo ${msg.archivo}...`)
                      }
                    >
                      <Feather name="file-text" size={18} color="#000" />
                      <Text style={styles.filePillText}>{msg.archivo}</Text>
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            );
          })}
        </ScrollView>

        {/*Barra inferior de entrada de texto*/}
        <View style={styles.inputWrapper}>
          <View style={styles.inputPill}>
            <TextInput
              style={styles.textInput}
              placeholder="Escribe un mensaje..."
              placeholderTextColor="#9E9E9E"
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={enviarMensaje}
            />
            <TouchableOpacity
              style={styles.sendButton}
              onPress={enviarMensaje}
              activeOpacity={0.8}
            >
              <Feather name="arrow-up" size={24} color="#FFF" />
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#CAFF70',
  },
  header: {
    backgroundColor: '#CAFF70',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: Platform.OS === 'android' ? 16 : 8,
    paddingBottom: 14,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  backButton: {
    marginRight: 12,
    padding: 4,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '400',
    color: '#000',
  },
  avatarContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#5B8DEF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  chatContainer: {
    flex: 1,
    backgroundColor: '#F4F4F4',
  },
  messagesList: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 14,
    paddingTop: 18,
    paddingBottom: 20,
  },
  userRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginBottom: 18,
  },
  userBubble: {
    backgroundColor: '#436EE8',
    borderRadius: 24,
    borderBottomRightRadius: 4,
    paddingHorizontal: 18,
    paddingVertical: 14,
    maxWidth: '78%',
    minWidth: 160,
  },
  userBubbleText: {
    color: '#FFF',
    fontSize: 15,
    lineHeight: 20,
  },
  botRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 18,
  },
  botAvatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#CFD6DC',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  botMessagesColumn: {
    flex: 1,
    alignItems: 'flex-start',
  },
  botBubble: {
    backgroundColor: '#CFD6DC',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 14,
    maxWidth: '92%',
  },
  botBubbleText: {
    color: '#000',
    fontSize: 15,
    lineHeight: 22,
  },
  filePill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#CFD6DC',
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 9,
    marginTop: 8,
  },
  filePillText: {
    color: '#000',
    fontSize: 13,
    marginLeft: 8,
  },
  inputWrapper: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: '#F4F4F4',
  },
  inputPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    borderWidth: 3,
    borderColor: '#4CC3FF',
    borderRadius: 32,
    height: 56,
    paddingLeft: 18,
    paddingRight: 6,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    color: '#000',
  },
  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#003B95',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
