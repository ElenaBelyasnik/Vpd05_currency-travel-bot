"""
Простой тестовый скрипт для проверки соединения с AllRatesToday API.
Используем requests с отключенной проверкой SSL и разными стратегиями.
"""

import requests
import sys
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

# Убираем предупреждения urllib3 о безопасности (не рекомендуется для продакшена)
disable_warnings(InsecureRequestWarning)

API_URL = "https://allratestoday.com/api/v1/rates"
API_KEY = "art_live_cFKgcfjOP1loAMNbVGZKapq78MbetDMB"

# Параметры запроса
params = {
    "source": "USD",
    "target": "EUR"
}

# Разные варианты User-Agent
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "python-requests/2.31.0"
]

def test_request(ua_index, verify_ssl):
    """
    Выполнить тестовый запрос.
    
    Args:
        ua_index: индекс User-Agent из списка
        verify_ssl: True для проверки сертификата, False для обхода
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": user_agents[ua_index]
    }
    
    print(f"\n--- Тест #{ua_index + 1} (Verify SSL: {verify_ssl}) ---")
    print(f"URL: {API_URL}")
    print(f"Params: {params}")
    print(f"User-Agent: {headers['User-Agent']}")
    
    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=headers,
            timeout=15,
            verify=verify_ssl  # Переключаем проверку SSL
        )
        
        print(f"\n✅ Успех!")
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text[:200]}...")  # Первые 200 символов
        
        return True
        
    except requests.exceptions.SSLError as e:
        print(f"\n❌ Ошибка SSL: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Ошибка соединения: {e}")
        return False
    except requests.exceptions.Timeout:
        print(f"\n❌ Таймаут запроса")
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {type(e).__name__}: {e}")
        return False

def main():
    print("=" * 60)
    print("ТЕСТ СОЕДИНЕНИЯ С AllRatesToday API")
    print("=" * 60)
    
    # Тест 1: Стандартный запрос с проверкой SSL
    result1 = test_request(0, verify_ssl=True)
    
    # Тест 2: Браузерный User-Agent с проверкой SSL
    result2 = test_request(1, verify_ssl=True)
    
    # Тест 3: Браузерный User-Agent БЕЗ проверки SSL
    result3 = test_request(1, verify_ssl=False)
    
    # Тест 4: Прямой запрос python-requests без проверки SSL
    result4 = test_request(2, verify_ssl=False)
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ:")
    print("=" * 60)
    print(f"1. Стандартный (SSL check): {'✅' if result1 else '❌'}")
    print(f"2. Браузерный (SSL check): {'✅' if result2 else '❌'}")
    print(f"3. Браузерный (NO SSL check): {'✅' if result3 else '❌'}")
    print(f"4. Python-requests (NO SSL check): {'✅' if result4 else '❌'}")
    
    if result3 or result4:
        print("\n🎉 Вывод: Проблема в SSL/TLS сертификатах или их проверке.")
        print("   В production нужно настроить certifi, а не отключать проверку.")
    else:
        print("\n⚠️ Вывод: Сервер блокирует запросы полностью (возможно, по IP).")

if __name__ == "__main__":
    main()
