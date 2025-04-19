#include <grpcpp/grpcpp.h>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
#include <queue>
#include <fstream>
#include <utility>
#include <climits>
#include "proto/service.grpc.pb.h"

int matrix[1000][1000];

void readMatrix(const std::string& filename) {
    std::ifstream file(filename);
    
    if (!file.is_open()) {
        std::cerr << "Error opening file: " << filename << std::endl;
        exit(1);
    }
    
    for (int i = 0; i < 1000; i++) {
        for (int j = 0; j < 1000; j++) {
            file >> matrix[i][j];
            matrix[i][j] = 1 - matrix[i][j];
        }
    }
    
    file.close();
}



namespace dijkstra_impl {

    using namespace std;

    struct Node {
        int x, y;
        int dist;
        
        Node(int _x, int _y, int _dist) : x(_x), y(_y), dist(_dist) {}
        
        bool operator>(const Node& other) const {
            return dist > other.dist;
        }
    };

    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    bool isValid(int x, int y, int rows, int cols) {
        return x >= 0 && x < rows && y >= 0 && y < cols;
    }

    vector<pair<int, int>> dijkstra(pair<int, int> start, pair<int, int> end) {

        int rows = 1000;
        int cols = 1000;
    
        vector<vector<int>> dist(rows, vector<int>(cols, 2e9));
    
        vector<vector<bool>> was(rows, vector<bool>(cols, false));
    
        vector<vector<pair<int, int>>> prev(rows, vector<pair<int, int>>(cols, {-1, -1}));
    
        priority_queue<Node, vector<Node>, greater<Node>> pq;
        dist[start.first][start.second] = 0;
        pq.push(Node(start.first, start.second, 0));
    
        while (!pq.empty()) {
            Node current = pq.top();
            pq.pop();
    
            int x = current.x;
            int y = current.y;
    
            if (x == end.first && y == end.second) {
                break;
            }

            if (was[x][y]) continue;
            was[x][y] = true;
            for (int i = 0; i < 4; i++) {
                int nx = x + dx[i];
                int ny = y + dy[i];
            
                if (isValid(nx, ny, rows, cols) && matrix[nx][ny] == 0) {
                    int new_dist = dist[x][y] + 1;
                
                    if (new_dist < dist[nx][ny]) {
                        dist[nx][ny] = new_dist;
                        prev[nx][ny] = {x, y};
                        pq.push(Node(nx, ny, new_dist));
                    }
                }
            }
        }
    
        vector<pair<int, int>> path;
        for (pair<int, int> at = end; at != make_pair(-1, -1); at = prev[at.first][at.second]) {
            path.push_back(at);
        }
        reverse(path.begin(), path.end());
        return path;
    }
}


using grpc::Server;
using grpc::ServerBuilder;

class PathServiceImpl final : public graph::PathService::Service {
    grpc::Status GetPath(grpc::ServerContext* context, const graph::PathRequest* request, graph::PathResponse* response) override {
        const auto& start = request->start();
        const auto& end = request->end();
        int x = start.x(), y = start.y();
        std::vector<std::pair<int, int>> path = dijkstra_impl::dijkstra({start.x(), start.y()}, {end.x(), end.y()});
        for (std::pair<int, int> p: path) {
            graph::Point* point = response->add_path_points();
            point->set_x(p.first);
            point->set_y(p.second);
        }
        return grpc::Status::OK;
    }
};

void RunServer() {
    std::string server_address("0.0.0.0:9999");
    PathServiceImpl service;

    grpc::ServerBuilder builder;
    builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);

    std::unique_ptr<Server> server(builder.BuildAndStart());
    std::cout << "Server listening on " << server_address << std::endl;
    server->Wait();
}

int main() {
    readMatrix("/root/server/matrix.txt");
    RunServer();
    return 0;
}