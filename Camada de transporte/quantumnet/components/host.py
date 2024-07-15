
from ..objects import Logger, Qubit

class Host():
    def __init__(self, host_id: int, probability_on_demand_qubit_create: float = 0.5, probability_replay_qubit_create: float = 0.5, max_qubits_create: int = 10, memory_size: int = 10) -> None:
        # Sobre a rede
        self._host_id = host_id
        self._connections = []
        # Sobre o host
        self._memory = []
        self._memory_size = memory_size
        self._max_qubits_create = max_qubits_create
        self._probability_on_demand_qubit_create = probability_on_demand_qubit_create
        self._probability_replay_qubit_create = probability_replay_qubit_create
        # Sobre a execução
        self.logger = Logger.get_instance()
    
    def __str__(self):
        return f'{self.host_id}'
    
    @property
    def host_id(self):
        """
        ID do host. Sempre um inteiro.

        Returns:
            int : Nome do host.
        """
        return self._host_id
    
    @property
    def connections(self):
        """
        Conexões do host.

        Returns:
            list : Lista de conexões.
        """
        return self._connections
    
    @property
    def memory(self):
        """
        Memória do host.

        Returns:
            list : Lista de qubits.
        """
        return self._memory
    
    def get_last_qubit(self):
        """
        Retorna o último qubit da memória.

        Returns:
            Qubit : Último qubit da memória.
        """
        try:
            q = self.memory[-1]
            self.memory.remove(q)
            return q
        except IndexError:
            raise Exception('Não há mais qubits na memória.')
    
    def add_connection(self, host_id_for_connection: int):
        """
        Adiciona uma conexão ao host. Uma conexão é um host_id, um número inteiro.

        Args:
            host_id_for_connection (int): Host ID do host que será conectado.
        """
        
        if type(host_id_for_connection) != int:
            raise Exception('O valor fornecido para host_id_for_connection deve ser um inteiro.')
        
        if host_id_for_connection not in self.connections:
            self.connections.append(host_id_for_connection),

    def add_qubit(self, qubit: Qubit):
        """
        Adiciona um qubit à memória do host.

        Args:
            qubit (Qubit): O qubit a ser adicionado.
        """
        
        self.memory.append(qubit)
        Logger.get_instance().debug(f'Qubit {qubit.qubit_id} adicionado à memória do Host {self.host_id}.')

