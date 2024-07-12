import networkx as nx
from ..objects import Logger, Qubit
from ..components import Host
from .layers import *
import random


class Network():
    """
    Um objeto para utilizar como rede.
    """
    def __init__(self) -> None:
        # Sobre a rede
        self._graph = nx.Graph()
        self._topology = None
        self._hosts = {}
        # Camadas
        self._application = ApplicationLayer()
        self._transport = TransportLayer()
        self._physical = PhysicalLayer(self)
        self._link = LinkLayer(self, self._physical)
        self._network = NetworkLayer(self, self._link, self._physical)
        # Sobre a execução
        self.logger = Logger.get_instance()
        self.count_qubit = 0
        #minimo e maximo
        self.max_prob = 1
        self.min_prob = 0.2

    @property
    def hosts(self):
        """
        Dicionário com os hosts da rede. No padrão {host_id: host}.

        Returns:
            dict : Dicionário com os hosts da rede.
        """
        return self._hosts
    
    @property
    def graph(self):
        """
        Grafo da rede.

        Returns:
            nx.Graph : Grafo da rede.
        """
        return self._graph
    
    @property
    def nodes(self):
        """
        Nós do grafo da rede.

        Returns:
            list : Lista de nós do grafo.
        """
        return self._graph.nodes()
    
    @property
    def edges(self):
        """
        Arestas do grafo da rede.

        Returns:
            list : Lista de arestas do grafo.
        """
        return self._graph.edges()
    
    # Camadas
    @property
    def physical(self):
        """
        Camada física da rede.

        Returns:
            PhysicalLayer : Camada física da rede.
        """
        return self._physical
    
    @property
    def linklayer(self):
        """
        Camada de enlace da rede.

        Returns:
            LinkLayer : Camada de enlace da rede.
        """
        return self._link
    
    @property 
    def networklayer(self):
        """
        Camada de rede da rede.

        Returns:
            NetworkLayer : Camada de rede da rede.
        """
        return self._network
    
    def draw(self):
        """
        Desenha a rede.
        """
        nx.draw(self._graph, with_labels=True)
    
    def add_host(self, host: Host):
        """
        Adiciona um host à rede no dicionário de hosts, e o host_id ao grafo da rede.
            
        Args:
            host (Host): O host a ser adicionado.
        """
        # Adiciona o host ao dicionário de hosts, se não existir
        if host.host_id not in self._hosts:        
            self._hosts[host.host_id] = host
            Logger.get_instance().debug(f'Host {host.host_id} adicionado aos hosts da rede.')
        else:
            raise Exception(f'Host {host.host_id} já existe nos hosts da rede.')
            
        # Adiciona o nó ao grafo da rede, se não existir
        if not self._graph.has_node(host.host_id):
            self._graph.add_node(host.host_id)
            Logger.get_instance().debug(f'Nó {host.host_id} adicionado ao grafo da rede.')
            
        # Adiciona as conexões do nó ao grafo da rede, se não existirem
        for connection in host.connections:
            if not self._graph.has_edge(host.host_id, connection):
                self._graph.add_edge(host.host_id, connection)
                Logger.get_instance().debug(f'Conexões do {host.host_id} adicionados ao grafo da rede.')
    
    def get_host(self, host_id: int) -> Host:
        """
        Retorna um host da rede.

        Args:
            host_id (int): ID do host a ser retornado.

        Returns:
            Host : O host com o host_id fornecido.
        """
        return self._hosts[host_id]

    def get_eprs(self):
        """
        Cria uma lista de qubits entrelaçados (EPRs) associadas a cada aresta do grafo.

        Returns:
            Um dicionários que armazena as chaves que são as arestas do grafo e os valores são as
              listas de qubits entrelaçados (EPRs) associadas a cada aresta. 
        """
        eprs = {}
        for edge in self.edges:
            eprs[edge] = self._graph.edges[edge]['eprs']
        return eprs
    
    def get_eprs_from_edge(self, alice: int, bob: int) -> list:
        """
        Retorna os EPRs de uma aresta específica.

        Args:
            alice (int): ID do host Alice.
            bob (int): ID do host Bob.
        Returns:
            list : Lista de EPRs da aresta.
        """
        edge = (alice, bob)
        return self._graph.edges[edge]['eprs']
    
    def remove_epr(self, alice: int, bob: int) -> list:
        """
        Remove um EPR de um canal.

        Args:
            channel (tuple): Canal de comunicação.
        """
        channel = (alice, bob)
        try:
            epr = self._graph.edges[channel]['eprs'].pop(-1)   
            return epr
        except IndexError:
            raise Exception('Não há Pares EPRs.')   
        
    def set_ready_topology(self, topology_name: str, *args: int) -> str:
        """
        Cria um grafo com uma das topologias prontas para serem utilizadas. 
        São elas: Grade, Linha, Anel. Os nós são numerados de 0 a n-1, onde n é o número de nós.

        Args: 
            topology_name (str): Nome da topologia a ser utilizada.
            **args (int): Argumentos para a topologia. Geralmente, o número de hosts.
        
        """
        # Nomeia a topologia da rede
        self._topology = topology_name
    
        # Cria o grafo da topologia escolhida
        if topology_name == 'Grade':
            if len(args) != 2:
                raise Exception('Para a topologia Grade, são necessários dois argumentos.')
            self._graph = nx.grid_2d_graph(*args)
        elif topology_name == 'Linha':
            if len(args) != 1:
                raise Exception('Para a topologia Linha, é necessário um argumento.')
            self._graph = nx.path_graph(*args)
        elif topology_name == 'Anel':
            if len(args) != 1:
                raise Exception('Para a topologia Anel, é necessário um argumento.')
            self._graph = nx.cycle_graph(*args)

        # Converte os labels dos nós para inteiros
        self._graph = nx.convert_node_labels_to_integers(self._graph)

        # Cria os hosts e adiciona ao dicionário de hosts
        for node in self._graph.nodes():
            self._hosts[node] = Host(node)
        self.start_hosts()
        self.start_channels()
        self.start_eprs()
    
    def start_hosts(self, num_qubits: int = 10):
        """
        Inicializa os hosts da rede.
        
        Args:
            num_qubits (int): Número de qubits a serem inicializados.
        """
        for host_id in self._hosts:
            for i in range(num_qubits):
                self.physical.create_qubit(host_id)
        print("Hosts inicializados")    


    def start_channels(self):
        """
        Inicializa os canais da rede.
        
        Args:
            prob_on_demand_epr_create (float): Probabilidade de criar um EPR sob demanda.
            prob_replay_epr_create (float): Probabilidade de criar um EPR de replay.
        """
        for edge in self.edges:
            self._graph.edges[edge]['prob_on_demand_epr_create'] = random.uniform(self.min_prob, self.max_prob)
            self._graph.edges[edge]['prob_replay_epr_create'] = random.uniform(self.min_prob, self.max_prob)
            self._graph.edges[edge]['eprs'] = list()
        print("Canais inicializados")
        

    def start_eprs(self, num_eprs: int = 10):
        """
        Inicializa os pares EPRs nas arestas da rede.

        Args:
            num_eprs (int): Número de pares EPR a serem inicializados para cada canal.
        """
        for edge in self.edges:
            for i in range(num_eprs):
                epr = self.physical.create_epr_pair()
                self._graph.edges[edge]['eprs'].append(epr)
                self.logger.debug(f'Par EPR {epr} adicionado ao canal.')
        print("Pares EPRs adicionados")
        
        
        
        
        
        