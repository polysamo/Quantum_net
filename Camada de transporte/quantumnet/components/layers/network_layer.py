import networkx as nx
from quantumnet.components import Host
from quantumnet.objects import Logger, Epr
from random import uniform


class NetworkLayer:
    def __init__(self, network, link_layer, physical_layer):
        """
        Inicializa a camada de rede.
        
        args:
            network : Network : Rede.
            link_layer : LinkLayer : Camada de enlace.
        """
        self._network = network
        self._link_layer = link_layer
        self._physical_layer = physical_layer
        self.logger = Logger.get_instance()

    def __str__(self):
        """ Retorna a representação em string da camada de rede. 
        
        returns:
            str : Representação em string da camada de rede."""
        return f'Network Layer'
    
    def verify_channels(self):
        """
        Verifica se todos os canais possuem pelo menos um par EPR.

        Returns:
            bool: True se todos os canais tiverem pelo menos um par EPR, False caso contrário.
        """
        for edge in self._network.graph.edges:
            if len(self._network.get_eprs_from_edge(edge[0], edge[1])) == 0:
                self.logger.log(f'No EPR pairs between {edge[0]} and {edge[1]}')
                return False
        self.logger.log(f'Há pelo menos 1 par EPR nesses canais')
        return True
    

    def verify_nodes(self):
        """
        Verifica se todos os nós possuem pelo menos 2 qubits.
        
        Returns:
            bool : True se todos os nós possuem pelo menos 2 qubits, False caso contrário.
        """
        for node in self._network.graph.nodes:
            host = self._network.get_host(node)
            if len(host.memory) < 2:
                self.logger.log(f'Nós {node} não apresentam nem 2 qubits pelo menos')
                return False
        self.logger.log('Todos os nós possuem pelo menos 2 qubits')
        return True

    def short_route_valid(self, Alice: int, Bob: int):
        """
        Escolhe a melhor rota entre dois hosts com critérios adicionais.
        
        args:
            Alice (int): ID do host de origem.
            Bob (int): ID do host de destino.
            
        returns:
            list or None: Lista com a melhor rota entre os hosts ou None se não houver rota válida.
        """
        if Alice is None or Bob is None:
            self.logger.log('IDs de hosts inválidos fornecidos.')
            return None
        
        if not self._network.graph.has_node(Alice) or not self._network.graph.has_node(Bob):
            self.logger.log(f'Um dos nós ({Alice} ou {Bob}) não existe no grafo.')
            return None
        
        try:
            # Calcula todas as menores rotas entre Alice e Bob
            all_shortest_paths = list(nx.all_shortest_paths(self._network.graph, Alice, Bob))
        except nx.NetworkXNoPath:
            self.logger.log(f'Sem rota encontrada entre {Alice} e {Bob}')
            return None
        
        # Verifica cada rota encontrada
        for path in all_shortest_paths:
            valid_path = True
            # Verifica cada canal (aresta) na rota
            for i in range(len(path) - 1):
                node = path[i]
                next_node = path[i + 1]
                # Verifica se o canal possui pelo menos 1 par EPR
                if len(self._network.get_eprs_from_edge(node, next_node)) < 1:
                    self.logger.log(f'Sem pares Eprs entre {node} e {next_node} na rota {path}')
                    valid_path = False
                    break
                # Verifica se o nó possui pelo menos 2 qubits
                host = self._network.get_host(node)
                if len(host.memory) < 2:
                    self.logger.log(f'Nó {node} não tem pelo menos 2 qubits na rota {path}')
                    valid_path = False
                    break
            
            # Se encontrou uma rota válida, retorna essa rota
            if valid_path:
                self.logger.log(f'Rota válida encontrada: {path}')
                return path
        
        # Se não encontrou nenhuma rota válida
        self.logger.log('Nenhuma rota válida encontrada.')
        return None

    

    def entanglement_swapping(self, Alice=None, Bob=None):
        """
        Realiza o Entanglement Swapping em toda a rota determinada pelo short_route_valid.
        
        args:
            Alice (int, optional): ID do host de origem. Se não fornecido, usa o primeiro nó da rota válida.
            Bob (int, optional): ID do host de destino. Se não fornecido, usa o último nó da rota válida.
                
        returns:
            bool: True se todos os Entanglement Swappings foram bem-sucedidos, False caso contrário.
        """
        # Determina a rota usando short_route_valid se Alice e Bob não forem fornecidos
        if Alice is None or Bob is None:
            route = self.short_route_valid(Alice, Bob)
            if route is None or len(route) < 2:
                self.logger.log('Não foi possível determinar uma rota válida.')
                return False
            Alice = route[0]
            Bob = route[-1]
        else:
            route = self.short_route_valid(Alice, Bob)
            if route is None or len(route) < 2:
                self.logger.log('Não foi possível determinar uma rota válida.')
                return False

        # Realiza o Entanglement Swapping em toda a rota por pares
        while len(route) > 1:
            node1 = route[0]
            node2 = route[1]
            if len(route) > 2:
                node3 = route[2]
            else:
                node3 = None

            if not self._network.graph.has_edge(node1, node2):
                self.logger.log(f'Canal entre {node1}-{node2} não existe')
                return False

            try:
                epr1 = self._network.get_eprs_from_edge(node1, node2)[0]
            except IndexError:
                self.logger.log(f'Não há pares EPRs suficientes entre {node1}-{node2}')
                return False

            if node3 is not None:
                if not self._network.graph.has_edge(node2, node3):
                    self.logger.log(f'Canal entre {node2}-{node3} não existe')
                    return False

                try:
                    epr2 = self._network.get_eprs_from_edge(node2, node3)[0]
                except IndexError:
                    self.logger.log(f'Não há pares EPRs suficientes entre {node2}-{node3}')
                    return False

                #Adquirir a fidelidade dos pares EPRs obtidos 
                fidelity1 = epr1.get_current_fidelity()
                fidelity2 = epr2.get_current_fidelity()
                
                #Probabilidade de sucesso do entanglement swapping 
                success_prob = fidelity1 * fidelity2 + (1 - fidelity1) * (1 - fidelity2)
                if uniform(0, 1) > success_prob:
                    self.logger.log(f'Entanglement Swapping falhou entre {node1}-{node2} e {node2}-{node3}')
                    return False

                #Registra e calcula uma nova fidelidade e cria um novo par EPR virtual com essa fidelidade
                new_fidelity = (fidelity1 * fidelity2) / ((fidelity1 * fidelity2) + (1 - fidelity1) * (1 - fidelity2))
                epr_virtual = Epr((node1, node3), new_fidelity)

                if not self._network.graph.has_edge(node1, node3):
                    self._network.graph.add_edge(node1, node3, eprs=[])

                #Adiciona o par EPR virtual ao canal entre os nós e remore os pares EPRs originais do canal
                self._network.physical.add_epr_to_channel(epr_virtual, (node1, node3))
                self._network.physical.remove_epr_from_channel(epr1, (node1, node2))
                self._network.physical.remove_epr_from_channel(epr2, (node2, node3))

                route.pop(1)
            else:
                route.pop(1)

        self.logger.log(f'Entanglement Swapping concluído com sucesso entre {Alice} e {Bob}')
        return True
