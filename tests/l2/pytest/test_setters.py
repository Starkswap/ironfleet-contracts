import pytest

from open_zeppelin.utils import uint


class TestSetMinDepositAmount:

    @pytest.mark.asyncio
    async def test_set_min(self, admiral, l2_keeper, user1):

        with pytest.raises(Exception):
            await user1.send_transaction(admiral.contract_address, 'set_min_deposit', calldata=[*uint(10000000)])

        await l2_keeper.send_transaction(admiral.contract_address, 'set_min_deposit', calldata=[*uint(10000000)])

    @pytest.mark.asyncio
    async def test_set_keeper(self, admiral, user1, l2_keeper):
        with pytest.raises(Exception):
            await user1.send_transaction(admiral.contract_address, 'set_keeper_address', calldata=[42])

        await l2_keeper.send_transaction(admiral.contract_address, 'set_keeper_address', calldata=[42])

    @pytest.mark.asyncio
    async def test_set_max_fleet_size(self, admiral, user1, l2_keeper):
        with pytest.raises(Exception):
            await user1.send_transaction(admiral.contract_address, 'set_max_fleet_size', calldata=[42])

        await l2_keeper.send_transaction(admiral.contract_address, 'set_max_fleet_size', calldata=[42])
    
    @pytest.mark.asyncio
    async def test_set_unload_batch_size(self, admiral, user1, l2_keeper):
        with pytest.raises(Exception):
            await user1.send_transaction(admiral.contract_address, 'set_unload_batch_size', calldata=[42])

        await l2_keeper.send_transaction(admiral.contract_address, 'set_unload_batch_size', calldata=[42])
