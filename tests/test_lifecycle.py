import pytest

async def get_token(client, username, password):
    res = await client.post(
        '/api/v1/auth/login',
        data={'username': username, 'password': password},
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    assert res.status_code == 200, f'Login failed for {username}: {res.text}'
    return res.json()['access_token']


async def place_order(client, token):
    payload = {
        'restaurant_id': 1,
        'delivery_address': 'Hostel 1, Room 202',
        'special_instructions': 'Leave at door',
        'items': [{'menu_item_id': 1, 'quantity': 1}],
    }
    res = await client.post(
        '/api/v1/orders/',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert res.status_code == 201
    return res.json()['id']


@pytest.mark.asyncio
async def test_order_full_lifecycle(client):
    student_token = await get_token(client, 'student@campus.edu', 'StudentPass123!')
    owner_token = await get_token(client, 'dhaba_owner@campus.edu', 'OwnerPass123!')
    rider_token = await get_token(client, 'rider@campus.edu', 'RiderPass123!')

    order_id = await place_order(client, student_token)

    # Kitchen progression
    res_conf = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'confirmed'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert res_conf.status_code == 200

    res_prep = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'preparing'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert res_prep.status_code == 200

    # Rider delivery progression
    res_pickup = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'out_for_delivery'},
        headers={'Authorization': f'Bearer {rider_token}'},
    )
    assert res_pickup.status_code == 200
    assert res_pickup.json()['delivery']['status'] == 'picked_up'

    res_deliv = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'delivered'},
        headers={'Authorization': f'Bearer {rider_token}'},
    )
    assert res_deliv.status_code == 200
    assert res_deliv.json()['delivery']['status'] == 'completed'


@pytest.mark.asyncio
async def test_customer_unauthorized_status_update(client):
    student_token = await get_token(client, 'student@campus.edu', 'StudentPass123!')
    order_id = await place_order(client, student_token)

    # Student cannot mark their order as delivered or confirmed
    res = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'delivered'},
        headers={'Authorization': f'Bearer {student_token}'},
    )
    assert res.status_code == 403
    assert 'Customers can only cancel their own pending orders' in res.json()['detail']


@pytest.mark.asyncio
async def test_owner_cannot_perform_delivery_transitions(client):
    student_token = await get_token(client, 'student@campus.edu', 'StudentPass123!')
    owner_token = await get_token(client, 'dhaba_owner@campus.edu', 'OwnerPass123!')
    order_id = await place_order(client, student_token)

    # Restaurant owner cannot transition to out_for_delivery
    res = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'out_for_delivery'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert res.status_code == 400
    assert 'Restaurant owners can only transition to' in res.json()['detail']


@pytest.mark.asyncio
async def test_rider_cannot_perform_kitchen_transitions(client):
    student_token = await get_token(client, 'student@campus.edu', 'StudentPass123!')
    rider_token = await get_token(client, 'rider@campus.edu', 'RiderPass123!')
    order_id = await place_order(client, student_token)

    # Rider cannot confirm or prepare orders
    res = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'confirmed'},
        headers={'Authorization': f'Bearer {rider_token}'},
    )
    assert res.status_code == 400
    assert 'Delivery partners can only transition to' in res.json()['detail']


@pytest.mark.asyncio
async def test_customer_cannot_cancel_after_preparation_starts(client):
    student_token = await get_token(client, 'student@campus.edu', 'StudentPass123!')
    owner_token = await get_token(client, 'dhaba_owner@campus.edu', 'OwnerPass123!')
    order_id = await place_order(client, student_token)

    # Owner moves order to preparing
    await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'preparing'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )

    # Student tries to cancel after kitchen preparation begins
    cancel_res = await client.patch(
        f'/api/v1/orders/{order_id}/status',
        json={'status': 'cancelled'},
        headers={'Authorization': f'Bearer {student_token}'},
    )
    assert cancel_res.status_code == 400
    assert 'Cannot cancel order once preparation has started' in cancel_res.json()['detail']
