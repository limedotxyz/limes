// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ILimesVault {
    function stakeOf(address account) external view returns (uint256);
}

contract LimesRegistry {
    uint256 public constant MIN_STAKE = 250_000 ether; // 250k LIME (18 decimals)

    struct Relay {
        address operator;
        string url;
        uint256 registeredAt;
    }

    ILimesVault public immutable vault;

    Relay[] private _relays;
    mapping(address => uint256) private _indexOf; // operator -> 1-based index
    mapping(address => bool) public isRegistered;

    event RelayRegistered(address indexed operator, string url);
    event RelayRemoved(address indexed operator);
    event RelayUpdated(address indexed operator, string newUrl);

    error NotStaked();
    error AlreadyRegistered();
    error NotRegistered();
    error EmptyUrl();

    constructor(address _vault) {
        vault = ILimesVault(_vault);
    }

    modifier onlyStaked() {
        if (vault.stakeOf(msg.sender) < MIN_STAKE) revert NotStaked();
        _;
    }

    function registerRelay(string calldata url) external onlyStaked {
        if (isRegistered[msg.sender]) revert AlreadyRegistered();
        if (bytes(url).length == 0) revert EmptyUrl();

        _relays.push(Relay({
            operator: msg.sender,
            url: url,
            registeredAt: block.timestamp
        }));
        _indexOf[msg.sender] = _relays.length; // 1-based
        isRegistered[msg.sender] = true;

        emit RelayRegistered(msg.sender, url);
    }

    function removeRelay() external {
        if (!isRegistered[msg.sender]) revert NotRegistered();

        uint256 idx = _indexOf[msg.sender] - 1;
        uint256 lastIdx = _relays.length - 1;

        if (idx != lastIdx) {
            _relays[idx] = _relays[lastIdx];
            _indexOf[_relays[idx].operator] = idx + 1;
        }

        _relays.pop();
        delete _indexOf[msg.sender];
        isRegistered[msg.sender] = false;

        emit RelayRemoved(msg.sender);
    }

    function updateRelay(string calldata url) external onlyStaked {
        if (!isRegistered[msg.sender]) revert NotRegistered();
        if (bytes(url).length == 0) revert EmptyUrl();

        uint256 idx = _indexOf[msg.sender] - 1;
        _relays[idx].url = url;

        emit RelayUpdated(msg.sender, url);
    }

    function getRelays() external view returns (Relay[] memory) {
        return _relays;
    }

    function relayCount() external view returns (uint256) {
        return _relays.length;
    }

    function getRelayByOperator(address operator) external view returns (Relay memory) {
        if (!isRegistered[operator]) revert NotRegistered();
        return _relays[_indexOf[operator] - 1];
    }
}
