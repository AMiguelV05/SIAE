import React, { useState } from 'react';
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
  Modal,
  Alert,
} from 'react-native';
import { Feather, Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';

const AVISOS_RECIENTES = [
  {
    id: '1',
    titulo: 'Nuevos formatos para reportes de servicio social 2025A',
    categoria: 'Servicio Social',
  },
  {
    id: '2',
    titulo: 'Convocatoria para beca',
    categoria: 'Becas',
  },
  {
    id: '3',
    titulo: 'Requisitos para titulación',
    categoria: 'Titulación',
  },
  {
    id: '4',
    titulo: 'Calendario de trámites escolares',
    categoria: 'General',
  },
];

const PARA_TI = [
  {
    id: '1',
    titulo: 'Fechas de aplicación de examen para acreditación del idioma inglés',
    categoria: 'Idiomas',
  },
  {
    id: '2',
    titulo: 'Registro de materias y horarios para el próximo ciclo escolar',
    categoria: 'Académico',
  },
];

export default function HomeScreen() {
  const router = useRouter();
  const { codigo } = useLocalSearchParams();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('Todos');
  const [showFilters, setShowFilters] = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);

  const codigoEstudiante = codigo || 'Estudiante';
  const categorias = ['Todos', 'Servicio Social', 'Becas', 'Titulación', 'Idiomas'];

  const filtrarItems = (lista) => {
    return lista.filter((item) => {
      const coincideTexto = item.titulo
        .toLowerCase()
        .includes(searchQuery.toLowerCase());
      const coincideCategoria =
        selectedCategory === 'Todos' || item.categoria === selectedCategory;
      return coincideTexto && coincideCategoria;
    });
  };

  const avisosFiltrados = filtrarItems(AVISOS_RECIENTES);
  const paraTiFiltrados = filtrarItems(PARA_TI);

  const handleLogout = () => {
    setMenuVisible(false);
    router.replace('/');
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar backgroundColor="#CAFF70" barStyle="dark-content" />

      {/*Cabecera verde lima*/}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>SIAE</Text>

        <View style={styles.headerRight}>
          {/*Avatar del usuario*/}
          <TouchableOpacity
            style={styles.avatarContainer}
            onPress={() => Alert.alert('Perfil', `Código: ${codigoEstudiante}`)}
          >
            <Ionicons name="person" size={28} color="#FFD2A6" />
          </TouchableOpacity>

          {/*Botón menú*/}
          <TouchableOpacity
            style={styles.hamburgerButton}
            onPress={() => setMenuVisible(true)}
            accessibilityLabel="Abrir menú"
          >
            <View style={styles.hamburgerLine} />
            <View style={styles.hamburgerLine} />
            <View style={styles.hamburgerLine} />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/*Sección: Secciones y carreras*/}
        <Text style={styles.sectionTitle}>Secciones y carreras</Text>

        <View style={styles.searchRow}>
          <View style={styles.searchPill}>
            <Feather name="search" size={22} color="#000" />
            <View style={styles.verticalDivider} />
            <TextInput
              style={styles.searchInput}
              placeholder="Buscar avisos o carreras..."
              placeholderTextColor="#888"
              value={searchQuery}
              onChangeText={setSearchQuery}
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')}>
                <Feather name="x" size={18} color="#555" />
              </TouchableOpacity>
            )}
          </View>

          <TouchableOpacity
            style={styles.filterButton}
            onPress={() => setShowFilters(!showFilters)}
          >
            <Feather name="sliders" size={26} color="#000" />
          </TouchableOpacity>
        </View>

        {/*Chips de filtro desplegables*/}
        {showFilters && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.filterChipsContainer}
          >
            {categorias.map((cat) => (
              <TouchableOpacity
                key={cat}
                style={[
                  styles.chip,
                  selectedCategory === cat && styles.chipActive,
                ]}
                onPress={() => setSelectedCategory(cat)}
              >
                <Text
                  style={[
                    styles.chipText,
                    selectedCategory === cat && styles.chipTextActive,
                  ]}
                >
                  {cat}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}

        {/*Sección: Avisos recientes*/}
        <Text style={styles.sectionTitle}>Avisos recientes</Text>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.horizontalCardsContainer}
        >
          {avisosFiltrados.map((aviso) => (
            <TouchableOpacity
              key={aviso.id}
              style={styles.recentCard}
              activeOpacity={0.85}
              onPress={() => Alert.alert(aviso.categoria, aviso.titulo)}
            >
              <View style={styles.recentCardImagePlaceholder}>
                <Ionicons name="image" size={54} color="#FFF" />
              </View>
              <View style={styles.recentCardTextContainer}>
                <Text style={styles.recentCardText} numberOfLines={5}>
                  {aviso.titulo}
                </Text>
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/*Sección: Para ti*/}
        <Text style={styles.sectionTitle}>Para ti</Text>

        {paraTiFiltrados.map((item) => (
          <TouchableOpacity
            key={item.id}
            style={styles.forYouCard}
            activeOpacity={0.85}
            onPress={() => Alert.alert(item.categoria, item.titulo)}
          >
            <View style={styles.forYouImagePlaceholder}>
              <Ionicons name="image" size={85} color="#FFF" />
            </View>
            <View style={styles.forYouFooter}>
              <Text style={styles.forYouText}>{item.titulo}</Text>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/*Modal del menú*/}
      <Modal
        visible={menuVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setMenuVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setMenuVisible(false)}
        >
          <TouchableOpacity activeOpacity={1} style={styles.drawerMenu}>
            <View style={styles.drawerHeader}>
              <Text style={styles.drawerTitle}>Menú SIAE</Text>
              <Text style={styles.drawerSubtitle}>Código: {codigoEstudiante}</Text>
            </View>

            <TouchableOpacity
              style={styles.drawerItem}
              onPress={() => {
                setMenuVisible(false);
                router.push({
                  pathname: '/chat',
                  params: { codigo: codigoEstudiante },
                });
              }}
            >
              <Feather name="message-circle" size={20} color="#000" />
              <Text style={styles.drawerItemText}>Chat</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.drawerItem}
              onPress={() => {
                setMenuVisible(false);
                Alert.alert('Ayuda', 'Centro de ayuda SIAE');
              }}
            >
              <Feather name="help-circle" size={20} color="#000" />
              <Text style={styles.drawerItemText}>Ayuda</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.drawerItem}
              onPress={() => {
                setMenuVisible(false);
                Alert.alert('Mi cuenta', `Código de estudiante: ${codigoEstudiante}`);
              }}
            >
              <Feather name="user" size={20} color="#000" />
              <Text style={styles.drawerItemText}>Mi cuenta</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.drawerItem, styles.logoutItem]}
              onPress={handleLogout}
            >
              <Feather name="log-out" size={20} color="#D93025" />
              <Text style={[styles.drawerItemText, { color: '#D93025' }]}>
                Cerrar sesión
              </Text>
            </TouchableOpacity>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
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
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'android' ? 16 : 8,
    paddingBottom: 14,
  },
  headerTitle: {
    fontSize: 34,
    fontWeight: '400',
    color: '#000',
    letterSpacing: 0.5,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatarContainer: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: '#5B8DEF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
    overflow: 'hidden',
  },
  hamburgerButton: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: 4,
  },
  hamburgerLine: {
    width: 34,
    height: 4,
    backgroundColor: '#000',
    marginVertical: 3,
    borderRadius: 2,
  },
  container: {
    flex: 1,
    backgroundColor: '#F4F4F4',
  },
  scrollContent: {
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 30,
  },
  sectionTitle: {
    fontSize: 21,
    fontWeight: '400',
    color: '#000',
    marginBottom: 12,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 18,
  },
  searchPill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.3,
    borderColor: '#222',
    borderRadius: 25,
    height: 46,
    paddingHorizontal: 14,
    backgroundColor: '#F4F4F4',
  },
  verticalDivider: {
    width: 1,
    height: '65%',
    backgroundColor: '#222',
    marginHorizontal: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: '#000',
  },
  filterButton: {
    marginLeft: 14,
    padding: 4,
  },
  filterChipsContainer: {
    marginBottom: 16,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: '#E0E0E0',
    marginRight: 8,
  },
  chipActive: {
    backgroundColor: '#38B6FF',
  },
  chipText: {
    fontSize: 13,
    color: '#333',
  },
  chipTextActive: {
    color: '#FFF',
    fontWeight: '600',
  },
  horizontalCardsContainer: {
    paddingBottom: 20,
    gap: 12,
  },
  recentCard: {
    width: 112,
    height: 185,
    backgroundColor: '#38B6FF',
    padding: 5,
    alignItems: 'center',
  },
  recentCardImagePlaceholder: {
    width: '100%',
    height: 75,
    backgroundColor: '#0066EE',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  recentCardTextContainer: {
    flex: 1,
    justifyContent: 'flex-start',
    paddingHorizontal: 2,
  },
  recentCardText: {
    fontSize: 12,
    color: '#000',
    textAlign: 'center',
    lineHeight: 15,
  },
  forYouCard: {
    width: '100%',
    marginBottom: 18,
    overflow: 'hidden',
  },
  forYouImagePlaceholder: {
    width: '100%',
    height: 115,
    backgroundColor: '#0066EE',
    justifyContent: 'center',
    alignItems: 'center',
  },
  forYouFooter: {
    backgroundColor: '#CFD6DC',
    paddingHorizontal: 10,
    paddingVertical: 10,
    minHeight: 54,
    justifyContent: 'center',
  },
  forYouText: {
    fontSize: 14,
    color: '#000',
    lineHeight: 19,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  drawerMenu: {
    width: '72%',
    backgroundColor: '#FFF',
    height: '100%',
    paddingTop: 50,
    paddingHorizontal: 20,
  },
  drawerHeader: {
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
    paddingBottom: 16,
    marginBottom: 16,
  },
  drawerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#000',
  },
  drawerSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  drawerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
  },
  drawerItemText: {
    fontSize: 16,
    color: '#000',
    marginLeft: 14,
  },
  logoutItem: {
    marginTop: 30,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    paddingTop: 20,
  },
  logoutItem: {
    marginTop: 30,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    paddingTop: 20,
  },
});