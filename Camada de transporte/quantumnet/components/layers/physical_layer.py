from ...objects import Logger, Qubit, Epr
from ...components import Host
from random import uniform
import random

class PhysicalLayer():
    def __init__(self, network, physical_layer_id: int = 0):
        """
        Inicializa a camada física.
        
        args:
            physical_layer_id : int : Id da camada física.
        """
        self.max_prob = 1
        self.min_prob = 0.2
        self._physical_layer_id = physical_layer_id
        self._network = network
        self._qubits = []
        self._failed_eprs = []
        self._initial_qubits_fidelity = random.uniform(self.min_prob, self.max_prob)
        self._count_qubit = 0
        self._count_epr = 0
        self.logger = Logger.get_instance()
        
    def __str__(self):
        """ Retorna a representação em string da camada física. 
        
        returns:
            str : Representação em string da camada física."""
        return f'Physical Layer {self.physical_layer_id}'
      
    @property
    def physical_layer_id(self):
        """
        Retorna o id da camada física.
        
        returns:
            int : Id da camada física.
        """
        return self._physical_layer_id
    
    @property
    def qubits(self):
        """
        Retorna os qubits da camada física.
        
        returns:
            list : Lista de qubits da camada física.
        """
        return self._qubits
    
    @property
    def failed_eprs(self):
        """
        Retorna os pares EPR que falharam.
        
        returns:
            dict : Dicionário de pares EPR que falharam.
        """
        return self._failed_eprs
    
    def create_qubit(self, host_id: int):
        """
        Cria um qubit e adiciona à memória do host especificado.

        Args:
            host_id (int): ID do host onde o qubit será criado.

        Raises:
            Exception: Se o host especificado não existir na rede.
        """
        if host_id not in self._network.hosts:
            raise Exception(f'Host {host_id} não existe na rede.')

        # Cria o qubit e adiciona à memória do host
        qubit_id = self._count_qubit
        qubit = Qubit(qubit_id)  # Fidelidade inicial gerada internamente
        self._network.hosts[host_id].add_qubit(qubit)
        self._count_qubit += 1
        self.logger.debug(f'Qubit {qubit_id} criado com fidelidade inicial {qubit.get_initial_fidelity()} e adicionado à memória do Host {host_id}.')

    #Possível função genérica para entrelaçar inúmeros qubits. GHZ, W, etc.
    def entangle_n_qubits(self, qubits: list):
        pass
    

    def create_epr_pair(self, fidelity: float = 1.0):
        """
        Cria um par de qubits entrelaçados.
        
        returns:
            Qubit, Qubit : Par de qubits entrelaçados.
        """
        epr = Epr(self._count_epr, fidelity)
        return epr

    def add_epr_to_channel(self, epr: Epr, channel: tuple):
        """
        Adiciona um par EPR ao canal.
        
        args:
            epr (Epr): Par EPR.
            channel (tuple): Canal.
        """
        u, v = channel
        if not self._network.graph.has_edge(u, v):
            self._network.graph.add_edge(u, v, eprs=[])
        self._network.graph.edges[u, v]['eprs'].append(epr)
        self.logger.debug(f'Par EPR {epr} adicionado ao canal {channel}.')
        
    def remove_epr_from_channel(self, epr: Epr, channel: tuple):
        """
        Remove um par EPR do canal.
        
        args:
            epr (Epr): Par EPR a ser removido.
            channel (tuple): Canal.
        """
        u, v = channel
        if not self._network.graph.has_edge(u, v):
            self.logger.debug(f'Channel {channel} does not exist.')
            return
        try:
            self._network.graph.edges[u, v]['eprs'].remove(epr)
            self.logger.debug(f'Par EPR {epr} removido do canal {channel}.')
        except ValueError:
            self.logger.debug(f'Par EPR {epr} não encontrado no canal {channel}.')


    def fidelity_measurement_only_one(self, qubit: Qubit):
        """
        Mede a fidelidade de um qubit.

        Args:
            qubit (Qubit): Qubit.

        Returns:
            float: Fidelidade do qubit.
        """
        fidelity = qubit.get_current_fidelity()
        self.logger.log(f'A fidelidade do qubit {qubit} é {fidelity}')
        return fidelity
    
    def fidelity_measurement(self, qubit1: Qubit, qubit2: Qubit):
        """
        Mede a fidelidade entre dois qubits.

        Args:
            qubit1 (Qubit): Qubit 1.
            qubit2 (Qubit): Qubit 2.

        Returns:
            float: Fidelidade entre os qubits.
        """
        fidelity = qubit1.get_current_fidelity() * qubit2.get_current_fidelity()
        self.logger.log(f'A fidelidade entre o qubit {qubit1} e o qubit {qubit2} é {fidelity}')
        return fidelity
    
    def entanglement_creation_heralding_protocol(self, alice: Host, bob: Host):
        """ 
        Protocolo de criação de emaranhamento com sinalização.
        
        returns:
            bool : True se o protocolo foi bem sucedido, False caso contrário.
        """
        # Alice e Bob criam um par EPR
        qubit1 = alice.get_last_qubit()
        qubit2 = bob.get_last_qubit()
        epr_fidelity = qubit1.get_current_fidelity() * qubit2.get_current_fidelity()
        epr =  self.create_epr_pair(epr_fidelity)
    
        # Checa a fidelidade
        fidelity = self.fidelity_measurement(qubit1, qubit2)
        
        alice_host_id = alice.host_id  # Acessa o ID do host diretamente
        bob_host_id = bob.host_id      # Acessa o ID do host diretamente
        
        # Pode dar errado tanto pela probabilidade, quanto pela fidelidade
        if fidelity >= 0.8:
            self._network.edges[(alice_host_id, bob_host_id)]['eprs'].append(epr)
            self.logger.log('O protocolo de criação de emaranhamento foi bem sucedido com a fidelidade necessária.')
            # Adicionar par EPR no canal
            return True
        elif fidelity < 0.8:
            self.failed_eprs.append(epr)
            self.logger.log('O protocolo de criação de emaranhamento foi bem sucedido, mas com fidelidade baixa.')
            return False

    def echp_on_demand(self, alice_host_id: int, bob_host_id: int):
        """
        Protocolo para a recriação de um entrelaçamento entre os qubits de acordo com a probabilidade de sucesso de demanda do par EPR criado
            
        Args: 
            alice_host_id (int) : ID do Host de Alice
            bob_host_id  (int) : ID do Host de Bob
            
        Returns:
            bool : True se o protocolo foi bem sucedido, False caso contrário.
        """
        # Obtendo os qubits de Alice e Bob
        qubit1 = self._network.hosts[alice_host_id].get_last_qubit()
        qubit2 = self._network.hosts[bob_host_id].get_last_qubit()
            
        # Acessando a fidelidade dos qubits
        fidelity_qubit1 = self.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self.fidelity_measurement_only_one(qubit2)
                
        # Probabilidade de Sucesso do ECHP: Prob_demand_epr_create * Fidelidade_qubit1 * Fidelidade_qubit2
        prob_on_demand_epr_create = self._network.edges[alice_host_id, bob_host_id]['prob_on_demand_epr_create']
        echp_success_probability = prob_on_demand_epr_create * fidelity_qubit1 * fidelity_qubit2
            
        if uniform(0, 1) < echp_success_probability:
            epr = self.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self._network.edges[alice_host_id, bob_host_id]['eprs'].append(epr)
            self.logger.log(f'A probabilidade de sucesso do ECHP é {echp_success_probability}')
            return True
        self.logger.log('A probabilidade de sucesso do ECHP falhou.')
        return False

    
    def echp_on_replay(self, alice_host_id: int, bob_host_id: int):

        """ 
        Protocolo para a recriação de um entrelaçamento entre os qubits de que já estavam perdendo suas caracteristicas.
        
        Args: 
            alice_host_id (int) : ID do Host de Alice
            bob_host_id  (int) : ID do Host de Bob
        
        Returns:
            bool : True se o protocolo foi bem sucedido, False caso contrário.

        """

        # Obtendo os qubits de Alice e Bob
        qubit1 = self._network.hosts[alice_host_id].get_last_qubit()
        qubit2 = self._network.hosts[bob_host_id].get_last_qubit()
        
        # Acessando a fidelidade dos qubits
        fidelity_qubit1 = self.fidelity_measurement_only_one(qubit1)
        fidelity_qubit2 = self.fidelity_measurement_only_one(qubit2)
               
        # Proabilidade de Sucesso do ECHP: Prob_replay_epr_create * Fidelidade_qubit1* Fidelidade_qubit2
        prob_replay_epr_create = self._network.edges[alice_host_id, bob_host_id]['prob_replay_epr_create']
        echp_success_probability = prob_replay_epr_create * fidelity_qubit1 * fidelity_qubit2
        
        if uniform(0, 1) < echp_success_probability:
            epr = self.create_epr_pair(fidelity_qubit1 * fidelity_qubit2)
            self._network.edges[alice_host_id, bob_host_id]['eprs'].append(epr)
            self.logger.log(f'A probabilidade de sucesso do ECHP é {echp_success_probability}')
            return True
        self.logger.log('A probabilidade de sucesso do ECHP falhou.')
        return False
    
    
    