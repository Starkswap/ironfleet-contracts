from open_zeppelin.utils import Signer, uint


# This class is a wrapper for user account
class Account(Signer):
    def __init__(self, private_key):
        super(Account, self).__init__(private_key)

    def set_contract(self, account_contract):
        self.contract = account_contract
        self.contract_address = account_contract.contract_address

    async def mint(self, erc20_contract, to_contract, amount: int):
        uint_amount = uint(amount)
        return await self.send_transaction(to=erc20_contract.contract_address, selector_name='mint',
                                           calldata=[to_contract.contract_address, *uint_amount])

    async def burn(self, erc20_contract, amount: int):
        return await self.transfer(erc20_contract, 0x0, amount)

    async def transfer(self, erc20_contract, to_user, amount: int):
        uint_amount = uint(amount)
        return await self.send_transaction(to=erc20_contract.contract_address, selector_name='transfer',
                                           calldata=[to_user.contract_address, *uint_amount])

    async def approve(self, erc20_contract, spender_address, amount: int):
        uint_amount = uint(amount)
        return await self.send_transaction(to=erc20_contract.contract_address, selector_name='approve',
                                           calldata=[spender_address, *uint_amount])

    async def depart(self, admiral, ship_idx):
        return await self.send_transaction(to=admiral.contract_address, selector_name='depart', calldata=[ship_idx])

    async def deposit_into_ship(self, conductor, amount: int):
        uint_amount = uint(amount)
        return await self.send_transaction(to=conductor.contract_address, selector_name='deposit',
                                           calldata=[*uint_amount])

    async def send_transaction(self, to, selector_name, calldata, nonce=None, max_fee=0):
        return await super(Account, self).send_transaction(account=self.contract, to=to, selector_name=selector_name,
                                                           calldata=calldata, nonce=nonce, max_fee=max_fee)
