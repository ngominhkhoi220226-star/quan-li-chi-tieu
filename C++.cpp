#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

using namespace std;

int main() {
    ifstream file("data.csv");
    string line;
    long long total = 0;

    if (file.is_open()) {
        while (getline(file, line)) {
            if (line.empty()) continue;
            
            stringstream ss(line);
            string date, category, content, amount_str;
            
            // Đọc cấu trúc 4 cột từ file CSV tạm thời
            getline(ss, date, ',');
            getline(ss, category, ',');
            getline(ss, content, ',');
            getline(ss, amount_str, ',');

            if (!amount_str.empty()) {
                total += stoll(amount_str); // Ép kiểu chuỗi thành số và cộng dồn
            }
        }
        file.close();
    }

    // Xuất tổng tiền ra file tạm total.txt để Python đọc
    ofstream outfile("total.txt");
    outfile << total;
    outfile.close();

    return 0;
}
